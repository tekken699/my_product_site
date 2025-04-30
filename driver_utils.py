# driver_utils.py
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_driver(headless: bool = True):
    options = Options()
    if headless:
        # Используем современный headless-режим
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Отключаем загрузку изображений для повышения производительности
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    # Подавляем лишние логи (например, ошибки USB)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        logging.error("Не удалось инициализировать драйвер: %s", e)
        raise
    return driver
