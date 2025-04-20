# promispb_parser.py

import logging
import time
import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from driver_utils import get_driver
from common_regex import DECIMAL_REGEX, INTEGER_REGEX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_promispb(query: str):
    encoded_query = quote(query)
    url = f"https://promispb.ru/search/?query={encoded_query}"
    logger.info("[PROMISPB DEBUG] Request URL: %s", url)
    
    driver = get_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".products__pr-price-base, .price-wrapper"))
        )
        time.sleep(0.3)
        page_source = driver.page_source
    except Exception as e:
        logger.error("[PROMISPB DEBUG] Ошибка при загрузке страницы: %s", e)
        page_source = ""
    finally:
        driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    product_elems = soup.find_all("div", class_="products__item")
    products = []
    
    for elem in product_elems:
        try:
            name_elem = elem.find("span", class_="products__item-info-name")
            name = name_elem.get_text(strip=True) if name_elem else "Без названия"
    
            availability = "В наличии"
            availability_div = elem.find("div", class_="products__available")
            if availability_div:
                out_of_stock = availability_div.find("div", class_="products__available-out-of-stock")
                if out_of_stock:
                    availability = out_of_stock.get_text(strip=True)
    
            price_numeric = 0.0
            price_display = ""
            price_wrapper = elem.find("div", class_="products__pr-price-base")
            if not price_wrapper:
                price_wrapper = elem.find("span", class_="price-wrapper")
            if not price_wrapper:
                price_query_div = elem.find("div", class_="products__zero-text")
                if price_query_div:
                    price_display = price_query_div.get_text(strip=True)
            elif price_wrapper:
                price_span = price_wrapper.find("span", class_="price")
                raw_price = price_span.get_text(strip=True) if price_span else ""
                if raw_price:
                    numbers = DECIMAL_REGEX.findall(raw_price)
                    if numbers:
                        price_numeric = float(numbers[0].replace(',', '.'))
                    else:
                        match = INTEGER_REGEX.search(raw_price)
                        price_numeric = float(match.group()) if match else 0.0
                    price_display = f"{price_numeric} ₽/шт."
    
            link_elem = elem.find("a", href=True)
            link = urljoin("https://promispb.ru/", link_elem["href"]) if link_elem else url
    
            img_tag = elem.find("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("data-srcset") or img_tag.get("src") or ""
                if img_url.startswith("/"):
                    img_url = urljoin("https://promispb.ru/", img_url)
    
            step = 1
            ratio_div = elem.find("div", class_="products__pr-price-ratio")
            if ratio_div:
                ratio_span = ratio_div.find("span", class_="js-stock-base-ratio")
                if ratio_span:
                    ratio_text = ratio_span.get_text(strip=True)
                    try:
                        step = int(ratio_text.replace(" ", ""))
                    except ValueError:
                        step = 1
            quantity = step
    
            products.append({
                "name": name,
                "price": price_numeric if price_numeric > 0 else None,
                "price_display": price_display,
                "site": "promispb",
                "link": link,
                "img_url": img_url,
                "quantity": quantity,
                "step": step,
                "availability": availability
            })
        except Exception as e:
            logger.error("Ошибка при парсинге товара promispb: %s", e)
    
    return products
