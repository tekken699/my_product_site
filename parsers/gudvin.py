from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import time
import re

def parse_gudvin(query):
    encoded_query = quote(query)
    url = f"https://gudvin-group.ru/?search={encoded_query}&s=1"
    
    # Настройки браузера в headless режиме
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    try:
        # Увеличиваем таймаут до 15 сек и используем несколько селекторов,
        # чтобы подстраховаться, если один селектор не сработает
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-card, .product-item, .product-snippet"))
        )
    except Exception as e:
        print("[GUDVIN DEBUG] Timeout waiting for elements:", e)
    
    time.sleep(1)  # Дополнительная задержка для полной загрузки страницы
    page_source = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(page_source, "html.parser")
    
    # Сначала ищем по первому селектору, затем используем альтернативный, если ничего не найдено
    product_elems = soup.find_all("div", class_="product-card")
    if not product_elems:
        product_elems = soup.select("div.product-item, div.product-snippet")
        print(f"[GUDVIN DEBUG] Использую альтернативный селектор, найдено {len(product_elems)} элементов")
    
    products = []
    for elem in product_elems:
        try:
            # Извлечение названия товара
            title_elem = elem.find("a", class_="product-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                img_elem = elem.find("img", alt=True)
                title = img_elem["alt"].strip() if img_elem and img_elem.has_attr("alt") else "Без названия"
    
            # Извлечение количества
            quantity_elem = elem.find("span", class_="product-snippet-data-quantity")
            if quantity_elem:
                match = re.search(r'\d+', quantity_elem.get_text(strip=True))
                quantity = int(match.group()) if match else 1
            else:
                quantity = 1
    
            # Извлечение цены (используем re.findall для поиска числа с десятичной точкой)
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
                            numbers = re.findall(r'\d+\.\d+', price_text)
                            price_value = float(numbers[0]) if numbers else 0.0
                        else:
                            price_value = 0.0
                else:
                    price_value = 0.0
            else:
                price_text = price_elem.get_text(strip=True)
                numbers = re.findall(r'\d+\.\d+', price_text)
                price_value = float(numbers[0]) if numbers else 0.0
    
            # Извлечение ссылки товара
            link_elem = elem.find("a", href=True)
            if not link_elem:
                continue
            link = urljoin("https://gudvin-group.ru/", link_elem["href"])
    
            # Извлечение URL изображения
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
    
            # Определение наличия товара
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
                "availability": availability
            })
        except Exception as e:
            print("Ошибка при парсинге товара Gudvin:", e)
    
    return products
