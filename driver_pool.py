# driver_pool.py
import queue
import logging
from driver_utils import get_driver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriverPool:
    def __init__(self, pool_size=10):  # Увеличиваем размер пула до 10
        self.pool = queue.Queue(maxsize=pool_size)
        self.pool_size = pool_size
        for _ in range(pool_size):
            driver = get_driver(headless=True)
            self.pool.put(driver)
        logger.info("Инициализирован пул из %d драйверов", pool_size)

    def acquire_driver(self, timeout=None):
        try:
            driver = self.pool.get(timeout=timeout)
            logger.debug("Драйвер получен из пула")
            return driver
        except queue.Empty:
            logger.error("Нет доступного драйвера в пуле!")
            raise Exception("Driver pool depleted")

    def release_driver(self, driver):
        try:
            driver.delete_all_cookies()
        except Exception as e:
            logger.error("Ошибка при удалении кук: %s", e)
        self.pool.put(driver)
        logger.debug("Драйвер возвращён в пул")

    def close_all(self):
        while not self.pool.empty():
            driver = self.pool.get()
            driver.quit()
        logger.info("Все драйверы закрыты")

# Глобальный объект пула
driver_pool = DriverPool(pool_size=10)
