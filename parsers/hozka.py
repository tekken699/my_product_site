import logging
import re
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from driver_pool import driver_pool
from common_regex import INTEGER_REGEX
from timer_utils import timer
from page_loader import load_page

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_hozka(query: str) -> List[Dict]:
    """
    Парсит результаты поиска с сайта Hozka.pro и возвращает список товаров.
    
    Логика:
      - Цена, указанная на сайте, используется первично.
      - Если найдено количество штук в упаковке (целое число > 1), цена делится на количество для расчёта цены за единицу.
      - Если упаковка не указана или равна 1, цена остаётся без изменений.
      - Если в содержимом товара встречается "Под заказ" или "Скоро появится", товар считается недоступным.
    
    Возвращает:
      List[Dict]: список товаров с полями:
          - "name": название товара
          - "price": цена (цена за штуку, если упаковка > 1)
          - "price_display": отформатированная строка, с "/шт.", если применимо
          - "site": источник (Hozka.pro)
          - "link": ссылка на товар
          - "img_url": ссылка для изображения товара
          - "quantity" и "step": количество товара (упаковка)
          - "availability": статус доступности товара
    """
    normalized_query = " ".join(query.split())
    encoded_query = quote(normalized_query)
    url = f"https://hozka.pro/search?search={encoded_query}"
    logger.info("Request URL: %s", url)

    with timer("Hozka: Driver acquisition"):
        driver = driver_pool.acquire_driver(timeout=10)

    try:
        with timer("Hozka: Page loading and waiting"):
            page_source = load_page(
                driver,
                url,
                css_selector="a[href^='/catalog/']",
                wait_time=15,
                sleep_after=0.3,
                attempts=3
            )
    except Exception as e:
        logger.error("Ошибка при загрузке страницы: %s", e)
        page_source = ""
    finally:
        driver.delete_all_cookies()
        driver_pool.release_driver(driver)

    products: List[Dict] = []
    with timer("Hozka: DOM parsing"):
        soup = BeautifulSoup(page_source, "html.parser")
        product_elems = soup.find_all("a", href=lambda href: href and href.startswith("/catalog/"))

    for elem in product_elems:
        product = _parse_product_element(elem)
        if product:
            products.append(product)
    logger.info("Parsed %d products", len(products))
    return products


def _parse_product_element(elem: BeautifulSoup) -> Optional[Dict]:
    """
    Извлекает данные о товаре из HTML-элемента и применяет обновлённую логику для цены и наличия.
    
    Логика:
      - Сначала используется цена, указанная на сайте.
      - Если найден элемент с количеством штук в упаковке (целое число > 1), считается цена за единицу:
            unit_price = total_price / количество
        Если упаковка не указана или равна 1, цена остаётся неизменной.
      - Если встречается текст "Под заказ" или "Скоро появится", статус availability меняется на "Не в наличии".
    
    Возвращает:
      Optional[Dict]: данные о товаре или None, если обязательные данные (например, название) не найдены.
    """
    try:
        raw_href = elem.get("href", "")
        if not raw_href.startswith("/catalog/") or "search" in raw_href:
            return None
        link = urljoin("https://hozka.pro/", raw_href)

        # Извлечение названия товара
        title_elem = elem.find("div", class_=lambda c: c and "line-clamp-2" in c)
        name = title_elem.get_text(strip=True) if title_elem else ""
        if not name:
            return None

        # Парсинг цены, указанной на сайте
        total_price = 0.0
        price_elem = elem.find("div", class_=lambda c: c and "font-bold" in c)
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            numbers = re.findall(r'\d+[,.]\d+', price_text)
            if numbers:
                total_price = float(numbers[0].replace(',', '.'))
            else:
                match = re.search(r'\d+', price_text)
                if match:
                    total_price = float(match.group())

        # По умолчанию, если количество неизвестно или равно 1, цена не делится
        step = 1
        unit_price = total_price

        # Поиск количества штук в упаковке (например, с классом "mt-3")
        quantity_elem = elem.find("div", class_=lambda c: c and "mt-3" in c)
        if quantity_elem:
            qty_text = quantity_elem.get_text(strip=True)
            m = INTEGER_REGEX.search(qty_text)
            if m:
                try:
                    step = int(m.group(0))
                except Exception as exc:
                    logger.error("Ошибка преобразования количества: %s", exc)
                    step = 1

        # Если упаковка состоит более чем из 1 штуки – вычисляем цену за единицу
        if step > 1:
            unit_price = total_price / step
            price_display = f"{unit_price:.2f} ₽/шт."
        else:
            price_display = f"{total_price:.2f} ₽"

        # Определение доступности: ищем индикаторы "Под заказ" или "Скоро появится"
        availability = "В наличии"
        if elem.find(text=re.compile(r"(Под заказ|Скоро появится)", re.IGNORECASE)):
            availability = "Не в наличии"

        # Извлечение ссылки на изображение
        img_url = ""
        img_tag = elem.find("img")
        if img_tag:
            img_url = img_tag.get("src") or ""
            if img_url.startswith("/"):
                img_url = urljoin("https://hozka.pro/", img_url)

        return {
            "name": name,
            "price": unit_price,
            "price_display": price_display,
            "site": "Hozka.pro",
            "link": link,
            "img_url": img_url,
            "quantity": step,
            "step": step,
            "availability": availability
        }
    except Exception as e:
        logger.error("Ошибка при парсинге товара Hozka: %s", e)
        return None
