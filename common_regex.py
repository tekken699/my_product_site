# common_regex.py
import re

# Регулярка для десятичных чисел, например "123,45" или "123.45"
DECIMAL_REGEX = re.compile(r'\d+[,.]\d+')
# Регулярка для целых чисел
INTEGER_REGEX = re.compile(r'\d+')

# Для ArtPlast: поиск упаковки вида "х <число> шт"
PACK_REGEX_ARTPLAST = re.compile(r'х\s*(\d+)\s*шт', re.IGNORECASE)
# Для Gudvin: поиск упаковки вида "уп: <число> шт"
PACK_REGEX_GUDVIN = re.compile(r'уп[:\s]*(\d+)\s*шт', re.IGNORECASE)
