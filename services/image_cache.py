import os
import hashlib
import asyncio
import aiohttp
from PIL import Image
import io

# Папка, куда будем сохранять кэшированные изображения
CACHE_DIR = os.path.join("static", "cache_images")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

async def async_get_cached_image(url):
    """
    Асинхронно получает изображение по URL, кэшируя результат.
    Возвращает байты PNG-изображения, если удалось, иначе None.
    """
    # Создаем уникальное имя файла по хэшу URL
    hash_name = hashlib.md5(url.encode('utf-8')).hexdigest() + ".png"
    filepath = os.path.join(CACHE_DIR, hash_name)
    
    # Если файл уже есть, пытаемся прочитать его
    if os.path.exists(filepath):
        try:
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            print(f"[DEBUG] Загружено из кэша: {filepath}")
            return image_bytes
        except Exception as e:
            print("Ошибка при чтении кэшированного изображения:", e)
    
    # Если изображения нет в кэше, выполняем скачивание
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, timeout=15) as response:
                response.raise_for_status()
                raw_data = await response.read()
                if len(raw_data) < 100:
                    print(f"[DEBUG] Недостаточный размер данных для {url}")
                    return None
                # Преобразуем данные в изображение и сохраняем в кэш
                image = Image.open(io.BytesIO(raw_data))
                image = image.convert("RGB")
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                image_data = buf.getvalue()
                with open(filepath, "wb") as f:
                    f.write(image_data)
                print(f"[DEBUG] Изображение сохранено в кэше: {filepath}")
                return image_data
        except Exception as e:
            print(f"[DEBUG] Ошибка скачивания изображения {url}: {e}")
            return None
