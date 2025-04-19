import asyncio
import concurrent.futures
from flask import Flask, request, jsonify, render_template, session, Response
from parsers import gudvin, promispb, hozka, artplast, newpackspb
from services.image_cache import async_get_cached_image

app = Flask(__name__)
# Задаём секретный ключ для работы с сессией (в продакшене используйте более надёжное значение)
app.secret_key = 'your-secret-key'


# Главная страница с формой поиска и блоком для отображения корзины
@app.route('/')
def index():
    return render_template('index.html')


# API-эндпоинт для обработки поискового запроса (параллельное выполнение парсеров)
@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Пустой запрос"}), 400

    results = {}
    # Маппинг магазина -> функция парсинга
    stores = {
        "gudvin": gudvin.parse_gudvin,
        "promispb": promispb.parse_promispb,
        "hozka": hozka.parse_hozka,
        "artplast": artplast.parse_artplast,
        "newpackspb": newpackspb.parse_newpackspb
    }
    # Запускаем все парсеры параллельно
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {store: executor.submit(func, query) for store, func in stores.items()}
        for store, future in futures.items():
            try:
                # Когда функция завершится — её результат сохраняется в results
                results[store] = future.result(timeout=30)
            except Exception as e:
                results[store] = []
                print(f"Error parsing {store}: {e}")
    return jsonify(results)


# Эндпоинт для отдачи кэшированного изображения
@app.route('/cached_image')
def cached_image():
    image_url = request.args.get("url")
    if not image_url:
        return "URL изображения не передан", 400

    # Создаем новый event loop для выполнения асинхронной функции
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    image_bytes = loop.run_until_complete(async_get_cached_image(image_url))
    loop.close()

    if image_bytes:
        return Response(image_bytes, mimetype="image/png")
    else:
        return "Ошибка загрузки изображения", 500


# Эндпоинты для работы с корзиной

# Получение корзины
@app.route('/api/cart', methods=['GET'])
def get_cart():
    cart = session.get("cart", [])
    return jsonify(cart)


# Добавление товара в корзину
@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    data = request.get_json()
    product = data.get("product")
    if not product or not product.get("link"):
        return jsonify({"error": "Нет данных о продукте или неопределён идентификатор товара"}), 400

    cart = session.get("cart", [])
    # Если товар уже есть – увеличиваем количество
    for item in cart:
        if item["link"] == product["link"]:
            item["quantity"] += product.get("quantity", 1)
            break
    else:
        product.setdefault("quantity", 1)
        cart.append(product)
    session["cart"] = cart
    return jsonify({"message": "Товар добавлен в корзину", "cart": cart})


# Удаление товара из корзины
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


# Обновление количества товара в корзине
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


# Оформление заказа (очищается корзина)
@app.route('/api/cart/checkout', methods=['POST'])
def cart_checkout():
    cart = session.get("cart", [])
    if not cart:
        return jsonify({"error": "Ваша корзина пуста"}), 400
    # Здесь можно добавить логику оформления заказа (уведомления, оплата и т.д.)
    session["cart"] = []
    return jsonify({"message": "Заказ оформлен, спасибо!", "cart": []})


if __name__ == '__main__':
    app.run(debug=True)
