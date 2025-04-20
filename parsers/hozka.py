# hozka_parser.py

import logging
import time
import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from driver_utils import get_driver
from common_regex import INTEGER_REGEX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_hozka(query: str):
    normalized_query = " ".join(query.split())
    encoded_query = quote(normalized_query)
    url = f"https://hozka.pro/search?search={encoded_query}"
    logger.info("[HOZKA DEBUG] Request URL: %s", url)
    
    driver = get_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/catalog/']"))
        )
        time.sleep(0.3)
        page_source = driver.page_source
    except Exception as e:
        logger.error("[HOZKA DEBUG] Ошибка при загрузке страницы: %s", e)
        page_source = ""
    finally:
        driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    product_elems = soup.find_all("a", href=lambda href: href and href.startswith("/catalog/"))
    products = []
    
    for elem in product_elems:
        try:
            raw_href = elem.get("href", "")
            if not raw_href.startswith("/catalog/") or "search" in raw_href:
                continue
            
            link = urljoin("https://hozka.pro/", raw_href)
            title_elem = elem.find("div", class_=lambda c: c and "line-clamp-2" in c)
            name = title_elem.get_text(strip=True) if title_elem else ""
            if not name:
                continue
            
            # Цена за упаковку
            total_price = 0.0
            price_elem = elem.find("div", class_=lambda c: c and "font-bold" in c)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                numbers = re.findall(r'\d+[,.]\d+', price_text)
                if numbers:
                    total_price = float(numbers[0].replace(',', '.'))
                else:
                    match = re.search(r'\d+', price_text)
                    total_price = float(match.group()) if match else 0.0
    
            # Извлечение количества в упаковке
            step = 1
            quantity_elem = elem.find("div", class_=lambda c: c and "mt-3" in c)
            if quantity_elem:
                qty_text = quantity_elem.get_text(strip=True)
                m = INTEGER_REGEX.search(qty_text)
                if m:
                    try:
                        step = int(m.group(0))
                    except:
                        step = 1
            unit_price = total_price / step if step > 0 else total_price
            price_display_unit = f"{unit_price:.2f} ₽/шт."
            
            img_tag = elem.find("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("src") or ""
                if img_url.startswith("/"):
                    img_url = urljoin("https://hozka.pro/", img_url)
    
            products.append({
                "name": name,
                "price": unit_price,
                "price_display": price_display_unit,
                "site": "Hozka.pro",
                "link": link,
                "img_url": img_url,
                "quantity": step,
                "step": step,
                "availability": "В наличии"
            })
        except Exception as e:
            logger.error("Ошибка при парсинге товара Hozka: %s", e)
    return products
