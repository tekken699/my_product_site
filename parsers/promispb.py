# Файл: parsers/promindus.py
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
    url = f"https://promispb.ru/search/?query={encoded_query}"  # Подставьте корректный URL, если он отличается
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    try:
        # Ждем появления хотя бы одного контейнера с ценой
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".products__pr-price-base, .price-wrapper"))
        )
    except Exception as e:
        print("[PROMINDUS DEBUG] Timeout waiting for price element:", e)
    
    time.sleep(1)
    page_source = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    # Предположим, что каждый товар находится в отдельном блоке с классом products__item (адаптируйте если нужно)
    product_elems = soup.find_all("div", class_="products__item")
    products = []
    for elem in product_elems:
        try:
            # Извлекаем название
            name_elem = elem.find("span", class_="products__item-info-name")
            name = name_elem.get_text(strip=True) if name_elem else "Без названия"
    
            # Извлекаем блок цены.
            price_wrapper = elem.find("div", class_="products__pr-price-base")
            if not price_wrapper:
                price_wrapper = elem.find("span", class_="price-wrapper")
            if price_wrapper:
                # Внутри ищем span.price
                price_span = price_wrapper.find("span", class_="price")
                raw_price = price_span.get_text(strip=True) if price_span else ""
            else:
                raw_price = ""
    
            if raw_price:
                # Исключаем лишние символы – ожидается формат, например, "4,90"
                numbers = re.findall(r'\d+[,.]\d+', raw_price)
                if numbers:
                    price_numeric = float(numbers[0].replace(',', '.'))
                else:
                    match = re.search(r'\d+', raw_price)
                    price_numeric = float(match.group()) if match else 0.0
                # Для отображения добавляем валюту и единицу, как на странице:
                # Можно также сохранить из блока всю верстку, но здесь мы собираем строку
                price_display = raw_price + " ₽/шт."
            else:
                price_numeric = 0.0
                price_display = ""
    
            # Извлекаем ссылку на товар
            link_elem = elem.find("a", href=True)
            link = urljoin("https://promispb.ru/", link_elem["href"]) if link_elem else url
    
            # Извлекаем картинку
            img_tag = elem.find("img")
            img_url = ""
            if img_tag and img_tag.has_attr("src"):
                img_url = img_tag["src"]
                if img_url.startswith("/"):
                    img_url = urljoin("https://promispb.ru/", img_url)
    
            products.append({
                "name": name,
                "price": price_numeric,
                "price_display": price_display,
                "site": "promispb",
                "link": link,
                "img_url": img_url,
                "quantity": 1,
                "availability": "В наличии"
            })
        except Exception as e:
            print("Ошибка при парсинге товара promispb:", e)
    
    return products
