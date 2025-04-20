# driver_utils.py
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_driver(headless: bool = True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Отключаем загрузку изображений для повышения производительности
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        logging.error("Не удалось инициализировать драйвер: %s", e)
        raise
    return driver
