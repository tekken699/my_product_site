# Файл: parsers/hozka.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import time
import re

def parse_hozka(query):
    normalized_query = " ".join(query.split())
    encoded_query = quote(normalized_query)
    url = f"https://hozka.pro/search?search={encoded_query}"
    print("[HOZKA DEBUG] Request URL:", url)
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/catalog/']"))
        )
    except Exception as e:
        print("[HOZKA DEBUG] Timeout waiting for catalog links:", e)
    
    time.sleep(1)
    page_source = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    product_elems = soup.find_all("a", href=lambda href: href and href.startswith("/catalog/"))
    
    products = []
    for elem in product_elems:
        try:
            # Извлечение и коррекция ссылки:
            raw_href = elem.get("href", "")
            if raw_href.count("https://") > 1:
                # Если встречается два URL, берем первый корректный
                parts = raw_href.split("https://")
                raw_href = "https://" + parts[1].split()[0]
            link = urljoin("https://hozka.pro/", raw_href)
            
            # Извлечение названия:
            title_elem = elem.find("div", class_=lambda c: c and "line-clamp-2" in c)
            name = title_elem.get_text(strip=True) if title_elem else ""
            if not name:
                continue  # пустые карточки пропускаем
            
            # Извлечение цены упаковки
            price_elem = elem.find("div", class_=lambda c: c and "font-bold" in c)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                numbers = re.findall(r'\d+[,.]\d+', price_text)
                if numbers:
                    total_price = float(numbers[0].replace(',', '.'))
                else:
                    match = re.search(r'\d+', price_text)
                    total_price = float(match.group()) if match else 0.0
                # Сохраняем оригинальное отображение цены упаковки
                price_display_pack = price_text
            else:
                total_price = 0.0
                price_display_pack = ""
    
            # Извлечение количества штук в упаковке
            quantity = 1
            quantity_elem = elem.find("div", class_=lambda c: c and "mt-3" in c)
            if quantity_elem:
                qty_text = quantity_elem.get_text(strip=True)
                m = re.search(r"(\d+)", qty_text)
                if m:
                    try:
                        quantity = int(m.group(1))
                    except:
                        quantity = 1
    
            # Вычисляем цену за штуку, если упаковка содержит более 1 штуки
            if quantity > 1 and total_price > 0:
                unit_price = total_price / quantity
                # Форматируем цену с двумя знаками после запятой, заменяя точку на запятую
                price_display = f"{unit_price:.2f}".replace('.', ',') + " ₽/шт."
            else:
                unit_price = total_price
                price_display = price_display_pack + " ₽/шт." if price_display_pack else ""
    
            # Извлечение картинки:
            img_tag = elem.find("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("src") or ""
                if img_url.startswith("/"):
                    img_url = urljoin("https://hozka.pro/", img_url)
    
            products.append({
                "name": name,
                "price": unit_price,
                "price_display": price_display,
                "site": "Hozka.pro",
                "link": link,
                "img_url": img_url,
                "quantity": quantity,
                "availability": "В наличии"
            })
        except Exception as e:
            print("Ошибка при парсинге товара Hozka:", e)
    return products
