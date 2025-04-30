# page_loader.py
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

def load_page(driver, url, css_selector, wait_time=15, sleep_after=0.3, attempts=3):
    """
    Загружает страницу по URL, ожидает появления элементов, удовлетворяющих css_selector.
    Производится до attempts попыток при ошибке.
    """
    for attempt in range(1, attempts + 1):
        try:
            driver.get(url)
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            )
            time.sleep(sleep_after)
            return driver.page_source
        except Exception as e:
            logger.error("Attempt %d/%d: Error loading %s: %s", attempt, attempts, url, e)
            if attempt == attempts:
                raise e
            else:
                time.sleep(1)
