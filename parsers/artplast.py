# artplast_parser.py

import logging
import time
import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from driver_utils import get_driver
from common_regex import DECIMAL_REGEX, INTEGER_REGEX, PACK_REGEX_ARTPLAST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_artplast(query: str):
    encoded_query = quote(query)
    url = f"https://spb.artplast.ru/search/?q={encoded_query}"
    logger.info("[ARTPLAST DEBUG] Request URL: %s", url)
    
    driver = get_driver()
    try:
        driver.get(url)
        # Ожидаем появления ссылок на товары
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/tovar/']"))
        )
        # Короткая задержка для динамичного контента
        time.sleep(0.3)
        page_source = driver.page_source
    except Exception as e:
        logger.error("[ARTPLAST DEBUG] Ошибка при загрузке страницы: %s", e)
        page_source = ""
    finally:
        driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    product_elems = soup.find_all("a", href=lambda href: href and href.startswith("/tovar/"))
    products = []
    seen = set()  # для исключения дублирования
    
    for elem in product_elems:
        try:
            link = urljoin("https://spb.artplast.ru/", elem.get("href"))
            if link in seen:
                continue
            seen.add(link)
            
            name_elem = elem.find_next("a", class_=lambda c: c and "hover:text-violet" in c)
            name = name_elem.get_text(strip=True) if name_elem else "Без названия"
            # Фильтрация по наименованию
            if query.lower() not in name.lower():
                continue
                
            # Извлечение цены
            price_numeric = 0.0
            price_display = ""
            price_div = elem.find_next("div", class_=lambda c: c and "min-w-" in c)
            if price_div:
                price_span = price_div.find("span", class_=lambda c: c and "tracking-wider" in c)
                if price_span:
                    price_text = price_span.get_text(strip=True)
                    numbers = DECIMAL_REGEX.findall(price_text)
                    if numbers:
                        price_numeric = float(numbers[0].replace(',', '.'))
                    else:
                        match = INTEGER_REGEX.search(price_text)
                        price_numeric = float(match.group()) if match else 0.0
                    price_display = price_text
                    
            avail_span = elem.find_next("span", class_=lambda c: c and ("text-green" in c or "text-orange" in c))
            availability = avail_span.get_text(strip=True) if avail_span else "Неизвестно"
    
            # Извлечение упаковки (минимальной партии)
            step = 1
            pack_spans = elem.find_all_next("span", class_="truncate")
            for span in pack_spans:
                alt_text = span.get_text(strip=True)
                m_alt = PACK_REGEX_ARTPLAST.search(alt_text)
                if m_alt:
                    step = int(m_alt.group(1))
                    break
            quantity = step  # количество равно упаковке
    
            img_tag = elem.find_next("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("src") or ""
                if img_url.startswith("/"):
                    img_url = urljoin("https://spb.artplast.ru/", img_url)
    
            products.append({
                "name": name,
                "price": price_numeric,
                "price_display": price_display,
                "site": "ArtPlast",
                "link": link,
                "img_url": img_url,
                "quantity": quantity,  
                "step": step,
                "availability": availability
            })
        except Exception as e:
            logger.error("Ошибка при парсинге товара ArtPlast: %s", e)
    return products
