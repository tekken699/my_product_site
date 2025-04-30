import asyncio
import logging
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User  # models.py должен содержать определение модели User
from parsers import gudvin, promispb, hozka, artplast, newpackspb
from services.image_cache import async_get_cached_image
from flask_caching import Cache

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Инициализация кэширования
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

# Настройка логирования
app.logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('app_debug.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.debug("Logging is setup correctly.")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------
# Основные маршруты
# ---------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

# ---------------------
# Вспомогательные функции для API поиска
# ---------------------

def is_refinement(new_query, base_query):
    new_tokens = new_query.lower().split()
    base_tokens = base_query.lower().split()
    if new_tokens == base_tokens:
        return False

    def is_numeric(token):
        try:
            float(token)
            return True
        except ValueError:
            return False

    base_non_numeric = [token for token in base_tokens if not is_numeric(token)]
    return all(token in new_tokens for token in base_non_numeric)

async def run_parsers(query, stores, timeout=6):
    loop = asyncio.get_event_loop()
    tasks = {}
    for store, func in stores.items():
        future = loop.run_in_executor(None, func, query)
        tasks[store] = asyncio.wait_for(future, timeout=timeout)
    results = {}
    for store, task in tasks.items():
        try:
            result = await task
            results[store] = result
        except asyncio.TimeoutError:
            results[store] = []
        except Exception as e:
            app.logger.error("Parser error for %s: %s", store, e)
            results[store] = []
    return results

# ---------------------
# API поиска
# ---------------------

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Пустой запрос"}), 400

    cache_key = f"search:{query.lower()}"
    cached_results = cache.get(cache_key)
    if cached_results is not None:
        app.logger.debug("Cache hit for query: %s", query)
        session["last_query"] = query
        session["last_cache_key"] = cache_key
        return jsonify(cached_results)

    last_query = session.get("last_query")
    last_cache_key = session.get("last_cache_key")
    last_results = cache.get(last_cache_key) if last_cache_key else None

    if last_query and last_results and is_refinement(query, last_query):
        new_tokens = query.lower().split()
        refined_results = {}
        for store, products in last_results.items():
            refined_products = []
            for product in products:
                product_name = product.get("name", "").lower()
                if all(token in product_name for token in new_tokens):
                    refined_products.append(product)
            refined_results[store] = refined_products

        cache.set(cache_key, refined_results)
        session["last_query"] = query
        session["last_cache_key"] = cache_key
        return jsonify(refined_results)

    stores = {
        "gudvin": gudvin.parse_gudvin,
        "promispb": promispb.parse_promispb,
        "hozka": hozka.parse_hozka,
        "artplast": artplast.parse_artplast,
        "newpackspb": newpackspb.parse_newpackspb
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(run_parsers(query, stores, timeout=6))
        app.logger.debug("Parsed results obtained.")
    except Exception as e:
        results = {}
        app.logger.error("Async parser error: %s", e)
    finally:
        loop.close()

    cache.set(cache_key, results)
    session["last_query"] = query
    session["last_cache_key"] = cache_key
    return jsonify(results)

@app.route('/api/search/update', methods=['POST'])
def api_search_update():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Пустой запрос"}), 400

    cache_key = f"search:{query.lower()}"
    current_results = cache.get(cache_key) or {}
    stores_to_update = {}
    for store, items in current_results.items():
        if not items:
            stores_to_update[store] = {"func": None}

    if not stores_to_update:
        return jsonify(current_results)

    full_stores = {
        "gudvin": gudvin.parse_gudvin,
        "promispb": promispb.parse_promispb,
        "hozka": hozka.parse_hozka,
        "artplast": artplast.parse_artplast,
        "newpackspb": newpackspb.parse_newpackspb
    }
    stores = {store: full_stores[store] for store in stores_to_update.keys()}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        updated_results = loop.run_until_complete(run_parsers(query, stores, timeout=20))
        for store, items in updated_results.items():
            if items:
                current_results[store] = items
        cache.set(cache_key, current_results)
    except Exception as e:
        app.logger.error("Update parser error: %s", e)
    finally:
        loop.close()

    return jsonify(current_results)

# ---------------------
# Кэшированное изображение
# ---------------------

@app.route('/cached_image')
def cached_image():
    image_url = request.args.get("url")
    if not image_url:
        return "URL изображения не передан", 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    image_bytes = loop.run_until_complete(async_get_cached_image(image_url))
    loop.close()

    if image_bytes:
        return Response(image_bytes, mimetype="image/png")
    else:
        return "Ошибка загрузки изображения", 500

# ---------------------
# API для работы с корзиной
# ---------------------

@app.route('/api/cart', methods=['GET'])
def get_cart():
    cart = session.get("cart", [])
    return jsonify(cart)

@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    data = request.get_json()
    product = data.get("product")
    if not product or not product.get("link"):
        return jsonify({"error": "Нет данных о продукте или неопределён идентификатор товара"}), 400

    try:
        step = product.get("step")
        if step is None:
            step = 1
        else:
            try:
                step = int(step)
                if step <= 0:
                    step = 1
            except (ValueError, TypeError):
                step = 1

        quantity = product.get("quantity", step)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = step

        if quantity < step:
            quantity = step

        cart = session.get("cart", [])
        updated = False
        for item in cart:
            if item.get("link") == product.get("link"):
                item["quantity"] += quantity
                updated = True
                break

        if not updated:
            product["quantity"] = quantity
            product["step"] = step
            cart.append(product)

        session["cart"] = cart
        return jsonify({"message": "Товар добавлен в корзину", "cart": cart})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cart/remove', methods=['POST'])
def cart_remove():
    data = request.get_json()
    product_link = data.get("link")
    if not product_link:
        return jsonify({"error": "Не задан идентификатор товара"}), 400
    cart = session.get("cart", [])
    cart = [item for item in cart if item.get("link") != product_link]
    session["cart"] = cart
    return jsonify({"message": "Товар удалён из корзины", "cart": cart})

@app.route('/api/cart/update', methods=['POST'])
def cart_update():
    data = request.get_json()
    product_link = data.get("link")
    new_quantity = data.get("quantity")
    if not product_link or new_quantity is None:
        return jsonify({"error": "Необходимо задать идентификатор товара и новое количество"}), 400
    cart = session.get("cart", [])
    for item in cart:
        if item.get("link") == product_link:
            item["quantity"] = new_quantity
            break
    session["cart"] = cart
    return jsonify({"message": "Корзина обновлена", "cart": cart})

@app.route('/api/cart/checkout', methods=['POST'])
def cart_checkout():
    cart = session.get("cart", [])
    if not cart:
        return jsonify({"error": "Ваша корзина пуста"}), 400
    session["cart"] = []
    return jsonify({"message": "Заказ оформлен, спасибо!", "cart": []})

@app.route('/api/cart/clear_all', methods=['POST'])
def clear_cart_all():
    session["cart"] = []
    return jsonify({"message": "Вся корзина очищена", "cart": []})

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Обновляем данные пользователя напрямую
        # Предполагается, что поля fio, phone, address, ip, inn существуют в модели User
        current_user.fio = request.form.get('fio', current_user.fio)
        current_user.phone = request.form.get('phone', current_user.phone)
        current_user.address = request.form.get('address', current_user.address)
        current_user.ip = request.form.get('ip', current_user.ip)
        current_user.inn = request.form.get('inn', current_user.inn)
        
        db.session.commit()
        # Перенаправляем на GET-версию профиля, чтобы обновленные данные загрузились
        return redirect(url_for('profile'))
    else:
        # Создаем словарь с данными для шаблона
        profile_data = {
            'fio': current_user.fio or current_user.username,
            'phone': current_user.phone or '',
            'address': current_user.address or '',
            'ip': current_user.ip or '',
            'inn': current_user.inn or ''
        }
        return render_template('profile.html', user=profile_data)





@app.route('/change_password', methods=['POST'])
def change_password():
    # Здесь логика смены пароля
    return redirect(url_for('profile'))



@app.route('/api/cart/clear_group', methods=['POST'])
def clear_cart_group():
    data = request.get_json()
    supplier = data.get("store")
    if not supplier:
        return jsonify({"error": "Не указан поставщик"}), 400
    cart = session.get("cart", [])
    new_cart = [item for item in cart if item.get("store") != supplier]
    session["cart"] = new_cart
    return jsonify({"message": f"Корзина для поставщика {supplier} очищена", "cart": new_cart})

# ---------------------
# Маршруты аутентификации (регистрация, логин, выход)
# ---------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            return render_template('register.html', error="Все поля обязательны.")
        if password != confirm_password:
            return render_template('register.html', error="Пароли не совпадают.")
        if User.query.filter((User.username == username) | (User.email == email)).first():
            return render_template('register.html', error="Пользователь с таким именем или email уже существует.")
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email').strip()
        password = request.form.get('password')
        if not username_or_email or not password:
            return render_template('login.html', error="Пожалуйста, заполните все поля.")
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if not user or not user.check_password(password):
            return render_template('login.html', error="Неправильное имя пользователя или пароль.")
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
    

@app.route('/users')
@login_required
def users():
    # Проверяем, является ли текущий пользователь администратором.
    if not getattr(current_user, 'intrig', False):
        abort(403)  # Если нет – возвращаем статус Forbidden (403)
    all_users = User.query.all()
    return render_template('users.html', users=all_users)



# ---------------------
# Запуск приложения
# ---------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаем таблицы в базе данных, если их ещё нет
    app.run(debug=True)
