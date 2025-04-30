# newpackspb_parser.py
import logging
import re
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from driver_pool import driver_pool
from common_regex import DECIMAL_REGEX, INTEGER_REGEX
from timer_utils import timer
from page_loader import load_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_newpackspb(query: str):
    encoded_query = quote(query)
    url = f"https://newpackspb.ru/?s={encoded_query}&post_type=product"
    logger.info("[NEWPACKSPB DEBUG] Request URL: %s", url)

    with timer("NewPacksPB: Driver acquisition"):
        driver = driver_pool.acquire_driver(timeout=10)

    try:
        with timer("NewPacksPB: Page loading and waiting"):
            page_source = load_page(driver, url, "a.woocommerce-LoopProduct-link",
                                    wait_time=15, sleep_after=0.3, attempts=3)
    except Exception as e:
        logger.error("[NEWPACKSPB DEBUG] Ошибка при загрузке страницы: %s", e)
        page_source = ""
    finally:
        driver.delete_all_cookies()
        driver_pool.release_driver(driver)

    with timer("NewPacksPB: DOM parsing"):
        soup = BeautifulSoup(page_source, "html.parser")
        product_elems = soup.find_all("a", class_="woocommerce-LoopProduct-link")
    
    products = []
    for elem in product_elems:
        try:
            name = elem.get_text(strip=True) if elem.get_text(strip=True) else "Без названия"
            link = elem.get("href") or url
            price_numeric = 0.0
            price_display = ""
            price_div = elem.find_next("div", class_=lambda c: c and "price-wrapper" in c)
            if price_div:
                price_span = price_div.find("span", class_=lambda c: c and "woocommerce-Price-amount" in c)
                if price_span:
                    bdi = price_span.find("bdi")
                    if bdi:
                        price_text = bdi.get_text(strip=True)
                        numbers = DECIMAL_REGEX.findall(price_text)
                        if numbers:
                            price_numeric = float(numbers[0].replace(',', '.'))
                        else:
                            match = INTEGER_REGEX.search(price_text)
                            price_numeric = float(match.group()) if match else 0.0
                        price_display = price_text
                    else:
                        price_numeric = 0.0
                        price_display = ""
                else:
                    price_numeric = 0.0
                    price_display = ""
            else:
                price_numeric = 0.0
                price_display = ""
            img_tag = elem.find_previous("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("src") or ""
                if img_url.startswith("/"):
                    img_url = urljoin("https://newpackspb.ru/", img_url)
            quantity = 1
            products.append({
                "name": name,
                "price": price_numeric,
                "price_display": price_display,
                "site": "NewPacksPB",
                "link": link,
                "img_url": img_url,
                "quantity": quantity,
                "availability": "В наличии"
            })
        except Exception as e:
            logger.error("Ошибка при парсинге товара NewPacksPB: %s", e)
    return products
