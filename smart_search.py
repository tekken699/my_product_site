import re
import pymorphy2
from rapidfuzz import fuzz
from nltk.stem.snowball import SnowballStemmer
from sqlalchemy import or_
from models import Product

# Инициализация pymorphy2 для лемматизации
morph = pymorphy2.MorphAnalyzer()
_cached = {}
_old_parse = morph.parse

def _cached_parse(word, *args, **kwargs):
    if word in _cached:
        return _cached[word]
    result = _old_parse(word, *args, **kwargs)
    _cached[word] = result
    return result

morph.parse = _cached_parse
stemmer = SnowballStemmer("russian")

# Словарь синонимов
SYNONYMS = {
    "пергамент": ["бумага для выпечки", "бумага для выпекания", "бумага"],
    "бумага": ["пергамент", "бумага для выпечки", "бумага для выпекания", "бумага для принтера"],
    "крышка": ["накрытие", "топпер"],
    "мешалка": ["размешиватель"],
    "контейнер для супа": ["супница"],
    "купольная": ["купол"],
    "двухслойные": ["двухслойные", "2 слойные", "2-слойные"],
    "стакан": ["чашка", "пластиковый стакан", "стеклянный стакан"]
}

# Токенизация: приведение к нижнему регистру, выделение буквенно-цифровых последовательностей
def tokenize(text):
    text = text.lower()
    return re.findall(r'\w+', text)

# Получение нормальных форм слова (лемматизация)
def get_normal_forms(token):
    forms = set()
    for p in morph.parse(token):
        forms.add(p.normal_form)
    return list(forms)

# Лемматизация набора токенов (без сохранения порядка)
def lemmatize_tokens(tokens):
    normalized_tokens = set()
    for token in tokens:
        normalized_tokens.update(get_normal_forms(token))
    return list(normalized_tokens)

# Стемминг токенов
def stem_tokens(tokens):
    words = set()
    for token in tokens:
        words.add(stemmer.stem(token))
    return list(words)

# Расширение набора токенов синонимами
def expand_synonyms(tokens):
    expanded = set(tokens)
    for token in tokens:
        token_lower = token.lower()
        if token_lower in SYNONYMS:
            for syn in SYNONYMS[token_lower]:
                expanded.add(syn)
                expanded.update(get_normal_forms(syn))
    return list(expanded)

# Нормализация текста: лемматизация с сохранением порядка
def normalize_text(text):
    tokens = tokenize(text)
    normalized = []
    for token in tokens:
        p = morph.parse(token)[0]
        normalized.append(p.normal_form)
    return " ".join(normalized)

# Преобразование строки в каноническую форму: замена токенов по словарю синонимов
def canonicalize_text(text):
    tokens = tokenize(text)
    canonical_tokens = []
    for token in tokens:
        if token in SYNONYMS:
            canonical_tokens.append(SYNONYMS[token][0])
        else:
            canonical_tokens.append(token)
    return " ".join(canonical_tokens)

# Функция вычисления схожести между запросом и названием товара
def compute_similarity(query, product_name):
    # Приводим запрос и название к каноническому и нормальному виду
    canon_query  = canonicalize_text(query)
    canon_product = canonicalize_text(product_name)
    norm_query   = normalize_text(canon_query)
    norm_product = normalize_text(canon_product)
    
    # Базовый показатель схожести с помощью RapidFuzz
    base_similarity = fuzz.token_set_ratio(norm_query, norm_product)
    
    # Дополнительные бонусы за полное совпадение, вхождение и совпадение первого токена
    if norm_query == norm_product:
        base_similarity += 50  # бонус за полное совпадение
    if norm_query in norm_product or norm_product in norm_query:
        base_similarity += 10
    if norm_product.startswith(norm_query + " ") or norm_product == norm_query:
        base_similarity += 20

    # Токенизация нормализованных строк
    query_tokens = tokenize(norm_query)
    product_tokens = tokenize(norm_product)
    
    # Учитываем порядок токенов в названии
    if product_tokens and query_tokens and (product_tokens[0] == query_tokens[0]):
        base_similarity += 15

    # Добавление веса точного вхождения "стакан" в название
    if "стакан" in query_tokens:
        if "стакан" in product_tokens:
            base_similarity += 20

    # Список стоп-слов
    stop_words = {"для", "и", "на", "в", "с", "по", "без", "от"}
    # Формируем список обязательных токенов из запроса
    required_tokens = [t for t in query_tokens if t not in stop_words]
    
    # Вычисляем коэффициенты по обязательным токенам с учетом сокращенных форм
    if required_tokens:
        multipliers = []
        for rt in required_tokens:
            if not product_tokens:
                multipliers.append(0)
            else:
                best = 0
                for pt in product_tokens:
                    # Если оба токена достаточно длинные (более 3 символов)
                    # и один является префиксом другого, считаем это полным совпадением (100)
                    if len(rt) > 3 and len(pt) > 3 and (rt.startswith(pt) or pt.startswith(rt)):
                        candidate = 100
                    else:
                        candidate = fuzz.ratio(rt, pt)
                    if candidate > best:
                        best = candidate
                multipliers.append(best / 100.0)
        multiplier = min(multipliers)
    else:
        multiplier = 1.0

    final_score = base_similarity * multiplier
    return final_score

# Функция генерации условий поиска для SQLAlchemy
def smart_search_query(query):
    tokens = tokenize(query)
    if not tokens:
        return []
    lemmas = lemmatize_tokens(tokens)
    stems  = stem_tokens(tokens)
    synonyms_original = expand_synonyms(tokens)
    synonyms_lemmas   = expand_synonyms(lemmas)
    synonyms_stems    = expand_synonyms(stems)
    combined_tokens = set(tokens + lemmas + stems + synonyms_original + synonyms_lemmas + synonyms_stems)
    conditions = []
    for token in combined_tokens:
        conditions.append(Product.name.ilike(f"%{token}%"))
        conditions.append(Product.search_query.ilike(f"%{token}%"))
    return conditions

# Функция выполнения поиска
def search_products_improved(query, available_only=False, similarity_threshold=60):
    conditions = smart_search_query(query)
    if not conditions:
        return []
    combined_condition = or_(*conditions)
    results = Product.query.filter(combined_condition).all()
    for product in results:
        product.similarity = compute_similarity(query, product.name)
    sorted_results = sorted(results, key=lambda p: p.similarity, reverse=True)
    filtered_results = [p for p in sorted_results if p.similarity >= similarity_threshold]
    if available_only:
        filtered_results = [p for p in filtered_results if "в наличии" in (p.availability or "").lower()]
    return filtered_results

# Функция группировки найденных товаров по поставщику
def group_results(products):
    groups = {}
    for product in products:
        store = product.site if product.site else "неизвестный поставщик"
        if store not in groups:
            groups[store] = {"count": 0, "products": []}
        groups[store]["products"].append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "price_display": product.price_display,
            "link": product.link,
            "img_url": product.img_url,
            "quantity": product.quantity,
            "step": product.step,
            "availability": product.availability,
            "similarity": product.similarity
        })
        groups[store]["count"] += 1
    for group in groups.values():
        group["products"].sort(key=lambda item: item["similarity"], reverse=True)
    return groups

# Основная функция поиска
def search_products(query, available_only=False, similarity_threshold=60, group=True):
    filtered_results = search_products_improved(query, available_only, similarity_threshold)
    if group:
        return group_results(filtered_results)
    else:
        results = []
        for product in filtered_results:
            results.append({
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "price_display": product.price_display,
                "link": product.link,
                "img_url": product.img_url,
                "quantity": product.quantity,
                "step": product.step,
                "availability": product.availability,
                "similarity": product.similarity,
                "site": product.site
            })
        return results

# Если модуль запускается напрямую, выполняем тестовый запрос
if __name__ == "__main__":
    test_query = "стакан"
    print("Исходный запрос:", test_query)
    print("Tokens:", tokenize(test_query))
    print("Lemmatized:", lemmatize_tokens(tokenize(test_query)))
    print("Stemmed:", stem_tokens(tokenize(test_query)))
    print("Expanded tokens:", expand_synonyms(tokenize(test_query)))
    print("Normalized query:", normalize_text(test_query))
    print("Search conditions:", smart_search_query(test_query))
    
    products = search_products(test_query, available_only=False, similarity_threshold=60, group=False)
    for product in products:
        print(f"ID: {product['id']}, Название: {product['name']}, Схожесть: {product['similarity']}")
