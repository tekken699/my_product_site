from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from datetime import datetime, timedelta
from models import db, Product
from parsers import gudvin, promispb, hozka, artplast, newpackspb
from zoneinfo import ZoneInfo

# Список подготовленных запросов
PREDEFINED_QUERIES = [
    "Микрофибра",
    "стакан",
    "крышка",
    "крышка для стакана",
    "пакет",
    "пакеты фасовочные",
    "Контейнер",
    "Крышка для контейнера",
    "Коробка под пирожное",
    "Пакет-майка",
    "Лента",
    "Наклейка",
    "Средство",
    "Химия",
    "Средство для очистки молочных систем",
    "Средство для кофемашины",
    "Кольца кодировочные",
    "Тарталетка",
    "Уголок",
    "Уголоки",
    "Держатель для стаканов",
    "Размешиватель",
    "Трубочки",
    "Вилка",
    "Вилки",
    "Ложка",
    "Ложки",
    "Нож",
    "Ножи",
    "Соусник",
    "Бумага для выпечки",
    "Пергамент",
    "Мешок кондитерский",
    "Бахилы",
    "Одноразовые шапочки",
    "Салфетки",
    "Тряпка",
    "Щетка",
    "Губка",
    "Мешок для мусора",
    "Мешки для мусора",
    "Пакет мусорный",
    "Чековая лента",
    "Этикет лента",
    "Перчатки",
    "Туалетная бумага",
    "освежитель воздуха",
    "Полотенце",
    "Зубочистки",
    "Тарелка",
    "Антисептик",
    "Сахар",
    "Сахар порц",
    "Соль",
    "Соль порц",
    "Перец",
    "Перец порц"
    
]

def background_parser_job():
    """
    Фоновый парсер для предопределённых запросов:
      - Для каждого запроса из PREDEFINED_QUERIES
      - Для каждого магазина из словаря stores
      - Вызывается соответствующий парсер, возвращающий список товаров
      - Для каждого товара выполняется поиск по полю link:
          • если товар уже есть – обновляются цена, доступность, время обновления
          • если товара нет – создаётся новый объект Product
      - После обработки всех товаров для запроса изменения фиксируются в БД
    """
    # Определяем словарь магазинов
    stores = {
        "gudvin": gudvin.parse_gudvin,
        "promispb": promispb.parse_promispb,
        "hozka": hozka.parse_hozka,
        "artplast": artplast.parse_artplast,
        "newpackspb": newpackspb.parse_newpackspb
    }
    
    # Обход предопределённых запросов
    for query in PREDEFINED_QUERIES:
        for store_name, parser_func in stores.items():
            try:
                products_list = parser_func(query)
                print(f"[{datetime.utcnow().isoformat()}] Обработал запрос '{query}' для магазина {store_name}, найдено товаров: {len(products_list)}")
                
                for prod in products_list:
                    # Поиск записи в БД по уникальному полю link
                    existing = Product.query.filter_by(link=prod["link"]).first()
                    if existing:
                        # Если изменились цена или доступность, обновляем запись
                        if existing.price != prod["price"] or existing.availability != prod["availability"]:
                            existing.price = prod["price"]
                            existing.price_display = prod.get("price_display", str(prod["price"]))
                            existing.availability = prod["availability"]
                            existing.last_updated = datetime.utcnow()
                            db.session.add(existing)
                    else:
                        # Создаем новую запись
                        new_product = Product(
                            name=prod["name"],
                            search_query=prod["name"].lower(),  # Заполняем поле поиска на основании имени
                            price=prod["price"],
                            price_display=prod.get("price_display", str(prod["price"])),
                            site=prod.get("site"),
                            link=prod["link"],
                            img_url=prod.get("img_url", ""),
                            quantity=prod.get("quantity", 1),
                            availability=prod["availability"],
                            last_updated=datetime.utcnow()
                        )
                        db.session.add(new_product)
                db.session.commit()
            except Exception as e:
                print(f"Ошибка парсера для запроса '{query}', магазин {store_name}: {e}")

def start_scheduler(app):
    """
    Запускает планировщик, который каждые 3 часа выполняет background_parser_job.
    Первый запуск запланирован через 3 часа от текущего времени.
    """
    tz = ZoneInfo("UTC")
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        func=lambda: (app.app_context().push(), background_parser_job()),
        trigger='interval',
        hours=3,
        next_run_time=datetime.utcnow().replace(tzinfo=tz) + timedelta(hours=3)
    )
    scheduler.start()
    app.logger.info("APScheduler запущен")
    atexit.register(lambda: scheduler.shutdown())
