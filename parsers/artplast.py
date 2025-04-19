from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import time
import re

def parse_artplast(query):
    encoded_query = quote(query)
    url = f"https://spb.artplast.ru/search/?q={encoded_query}"
    print("[ARTPLAST DEBUG] Request URL:", url)
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/tovar/']"))
        )
    except Exception as e:
        print("[ARTPLAST DEBUG] Timeout waiting for products:", e)
    
    time.sleep(1)
    page_source = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    product_elems = soup.find_all("a", href=lambda href: href and href.startswith("/tovar/"))
    
    products = []
    for elem in product_elems:
        try:
            link = urljoin("https://spb.artplast.ru/", elem.get("href"))
            name_elem = elem.find_next("a", class_=lambda c: c and "hover:text-violet" in c)
            name = name_elem.get_text(strip=True) if name_elem else "Без названия"
    
            price_div = elem.find_next("div", class_=lambda c: c and "min-w-" in c)
            if price_div:
                price_span = price_div.find("span", class_=lambda c: c and "tracking-wider" in c)
                if price_span:
                    price_text = price_span.get_text(strip=True)
                    numbers = re.findall(r'\d+[,.]\d+', price_text)
                    if numbers:
                        price_numeric = float(numbers[0].replace(',', '.'))
                    else:
                        match = re.search(r'\d+', price_text)
                        price_numeric = float(match.group()) if match else 0.0
                    price_display = price_text
                else:
                    price_numeric = 0.0
                    price_display = ""
            else:
                price_numeric = 0.0
                price_display = ""
    
            avail_span = elem.find_next("span", class_=lambda c: c and ("text-green" in c or "text-orange" in c))
            availability = avail_span.get_text(strip=True) if avail_span else "Неизвестно"
    
            qty_span = elem.find_next("span", class_=lambda c: c and "text-violet" in c)
            quantity = 1
            if qty_span:
                qty_text = qty_span.get_text(strip=True)
                m = re.search(r"(\d+)", qty_text)
                if m:
                    try:
                        quantity = int(m.group(1))
                    except:
                        quantity = 1
    
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
                "availability": availability
            })
        except Exception as e:
            print("Ошибка при парсинге товара ArtPlast:", e)
    
    return products
