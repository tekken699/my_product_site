from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import time
import re

def parse_promispb(query):
    encoded_query = quote(query)
    url = f"https://promispb.ru/search/?query={encoded_query}"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".products__pr-price-base, .price-wrapper"))
        )
    except Exception as e:
        print("[PROMINDUS DEBUG] Timeout waiting for price element:", e)
    
    time.sleep(0.5)
    page_source = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    product_elems = soup.find_all("div", class_="products__item")
    products = []
    for elem in product_elems:
        try:
            # Извлекаем название товара
            name_elem = elem.find("span", class_="products__item-info-name")
            name = name_elem.get_text(strip=True) if name_elem else "Без названия"
    
            # Извлекаем состояние товара (наличие)
            availability = "В наличии"  # Значение по умолчанию
            availability_div = elem.find("div", class_="products__available")
            if availability_div:
                out_of_stock = availability_div.find("div", class_="products__available-out-of-stock")
                if out_of_stock:
                    availability = out_of_stock.get_text(strip=True)
    
            # Извлекаем цену
            price_wrapper = elem.find("div", class_="products__pr-price-base")
            if not price_wrapper:
                price_wrapper = elem.find("span", class_="price-wrapper")
            price_numeric = 0.0
            price_display = ""
    
            # Проверяем, указана ли "Цена по запросу"
            price_query_div = elem.find("div", class_="products__zero-text")
            if price_query_div:
                price_display = price_query_div.get_text(strip=True)
            elif price_wrapper:
                price_span = price_wrapper.find("span", class_="price")
                raw_price = price_span.get_text(strip=True) if price_span else ""
                if raw_price:
                    numbers = re.findall(r'\d+[,.]\d+', raw_price)
                    if numbers:
                        price_numeric = float(numbers[0].replace(',', '.'))
                    else:
                        match = re.search(r'\d+', raw_price)
                        price_numeric = float(match.group()) if match else 0.0
                    price_display = f"{price_numeric} ₽/шт."
    
            # Извлекаем ссылку на товар
            link_elem = elem.find("a", href=True)
            link = urljoin("https://promispb.ru/", link_elem["href"]) if link_elem else url
    
            # Извлекаем изображение
            img_tag = elem.find("img")
            img_url = ""
            if img_tag:
                # Используем атрибуты data-src, data-srcset, затем src
                img_url = img_tag.get("data-src") or img_tag.get("data-srcset") or img_tag.get("src") or ""
                if img_url.startswith("/"):
                    img_url = urljoin("https://promispb.ru/", img_url)
    
            # Извлекаем упаковку – ищем элемент с классом "js-stock-base-ratio"
            step = 1
            ratio_div = elem.find("div", class_="products__pr-price-ratio")
            if ratio_div:
                ratio_span = ratio_div.find("span", class_="js-stock-base-ratio")
                if ratio_span:
                    ratio_text = ratio_span.get_text(strip=True)
                    try:
                        # Удаляем пробелы (например, "1 000" становится "1000")
                        step = int(ratio_text.replace(" ", ""))
                    except ValueError:
                        step = 1
            quantity = step  # начальное количество = упаковка
    
            products.append({
                "name": name,
                "price": price_numeric if price_numeric > 0 else None,  # Отображаем None, если "Цена по запросу"
                "price_display": price_display,  # Отображаем либо цену, либо "Цена по запросу"
                "site": "promispb",
                "link": link,
                "img_url": img_url,
                "quantity": quantity,
                "step": step,
                "availability": availability  # Отображает "Нет в наличии", если товара нет
            })
        except Exception as e:
            print("Ошибка при парсинге товара promispb:", e)
    
    return products
