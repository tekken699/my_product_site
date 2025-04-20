# newpackspb_parser.py

import logging
import time
import re
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from driver_utils import get_driver
from common_regex import DECIMAL_REGEX, INTEGER_REGEX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_newpackspb(query: str):
    encoded_query = quote(query)
    url = f"https://newpackspb.ru/?s={encoded_query}&post_type=product"
    logger.info("[NEWPACKSPB DEBUG] Request URL: %s", url)
    
    driver = get_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.woocommerce-LoopProduct-link"))
        )
        time.sleep(0.3)
        page_source = driver.page_source
    except Exception as e:
        logger.error("[NEWPACKSPB DEBUG] Ошибка при загрузке страницы: %s", e)
        page_source = ""
    finally:
        driver.quit()
    
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
    
            quantity = 1  # По умолчанию упаковка = 1 шт.
    
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
