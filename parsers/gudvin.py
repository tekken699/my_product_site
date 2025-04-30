# gudvin_parser.py
import logging
import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from driver_pool import driver_pool
from common_regex import DECIMAL_REGEX, INTEGER_REGEX, PACK_REGEX_GUDVIN
from timer_utils import timer
from page_loader import load_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_gudvin(query: str):
    encoded_query = quote(query)
    url = f"https://gudvin-group.ru/?search={encoded_query}&s=1"
    logger.info("[GUDVIN DEBUG] Request URL: %s", url)

    with timer("Gudvin: Driver acquisition"):
        driver = driver_pool.acquire_driver(timeout=10)

    try:
        with timer("Gudvin: Page loading and waiting"):
            page_source = load_page(driver, url, ".product-card, .product-item, .product-snippet",
                                    wait_time=15, sleep_after=0.3, attempts=3)
    except Exception as e:
        logger.error("[GUDVIN DEBUG] Ошибка при загрузке страницы: %s", e)
        page_source = ""
    finally:
        driver.delete_all_cookies()
        driver_pool.release_driver(driver)

    with timer("Gudvin: DOM parsing"):
        soup = BeautifulSoup(page_source, "html.parser")
        product_elems = soup.find_all("div", class_="product-card")
        if not product_elems:
            product_elems = soup.select("div.product-item, div.product-snippet")
            logger.info("[GUDVIN DEBUG] Использую альтернативный селектор, найдено %d элементов", len(product_elems))
    
    products = []
    for elem in product_elems:
        try:
            title_elem = elem.find("a", class_="product-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                img_elem = elem.find("img", alt=True)
                title = img_elem["alt"].strip() if img_elem and img_elem.has_attr("alt") else "Без названия"
            step = 1
            quantity_elem = elem.find("span", class_="product-snippet-data-quantity")
            if quantity_elem:
                text_quantity = quantity_elem.get_text(" ", strip=True)
                m = PACK_REGEX_GUDVIN.search(text_quantity)
                if m:
                    step = int(m.group(1))
            quantity = step
            price_value = 0.0
            price_elem = elem.find("span", class_="price-value")
            if not price_elem:
                price_elem = elem.find("div", class_="product-price")
            if not price_elem:
                price_container = elem.find("div", class_="product-snippet-price")
                if price_container:
                    meta_price = price_container.find("meta", itemprop="price")
                    if meta_price and meta_price.has_attr("content"):
                        price_value = float(meta_price["content"])
                    else:
                        span_price = price_container.find("span")
                        if span_price:
                            price_text = span_price.get_text(strip=True)
                            numbers = DECIMAL_REGEX.findall(price_text)
                            price_value = float(numbers[0]) if numbers else 0.0
                        else:
                            price_value = 0.0
                else:
                    price_value = 0.0
            else:
                price_text = price_elem.get_text(strip=True)
                numbers = DECIMAL_REGEX.findall(price_text)
                price_value = float(numbers[0]) if numbers else 0.0
            link_elem = elem.find("a", href=True)
            if not link_elem:
                continue
            link = urljoin("https://gudvin-group.ru/", link_elem["href"])
            img_url = None
            img_container = elem.find("div", class_="product-snippet-img")
            if img_container:
                img_tag = img_container.find("img")
                if img_tag and img_tag.has_attr("src"):
                    img_url = urljoin("https://gudvin-group.ru/", img_tag["src"])
            else:
                img_tag = elem.find("img")
                if img_tag and img_tag.has_attr("src"):
                    img_url = img_tag["src"]
            availability = "Неизвестно"
            avail_link = elem.find("link", itemprop="availability")
            if avail_link and avail_link.has_attr("href"):
                href_val = avail_link["href"].strip()
                if href_val == "http://schema.org/InStock":
                    availability = "В наличии"
                elif href_val == "http://schema.org/OutOfStock":
                    availability = "Нет в наличии"
                elif href_val == "http://schema.org/PreOrder":
                    availability = "Под заказ"
                else:
                    availability = href_val
            else:
                status_elem = elem.find("span", class_="product-snippet-data-status")
                if status_elem:
                    text_status = status_elem.get_text(strip=True).lower()
                    if "в наличии" in text_status:
                        availability = "В наличии"
                    elif "под заказ" in text_status:
                        availability = "Под заказ"
                    else:
                        availability = text_status.capitalize()
            products.append({
                "name": title,
                "price": price_value,
                "site": "Gudvin Group",
                "link": link,
                "img_url": img_url,
                "quantity": quantity,
                "step": step,
                "availability": availability
            })
        except Exception as e:
            logger.error("Ошибка при парсинге товара Gudvin: %s", e)
    return products
