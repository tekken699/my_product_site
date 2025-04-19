// Глобальные переменные для хранения результатов поиска и текущего номера страницы для каждого магазина
let globalData = null;
let storePages = {}; // Например: { "gudvin": 0, "promispb": 0, ... }, изначально все нули

// Функция выполнения поиска: отправляем AJAX-запрос на /api/search
async function performSearch() {
  const query = document.getElementById("search-input").value.trim();
  if (!query) {
    alert("Введите поисковый запрос");
    return;
  }
  
  // Считываем фильтры: минимальная и максимальная цена и опцию сортировки
  const minPrice = parseFloat(document.getElementById("min-price").value) || 0;
  const maxPrice = parseFloat(document.getElementById("max-price").value) || Infinity;
  const sortOption = document.getElementById("sort").value;
  
  // Выводим сообщение о загрузке
  document.getElementById("results").innerHTML = "<p>Загрузка товаров...</p>";
  
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });
    const data = await response.json();
    
    // Сохраняем результаты глобально
    globalData = data;
    // Сбросим пагинацию для нового запроса
    storePages = {};
    displayStoreProducts(minPrice, maxPrice, sortOption);
    // Прокручиваем страницу так, чтобы контейнер результатов оказался в поле зрения
    document.getElementById("results").scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    console.error("Ошибка запроса:", error);
    document.getElementById("results").innerHTML = "<p>Ошибка загрузки товаров</p>";
  }
}

// Функция отображения результатов по магазинам с постраничностью (6 карточек на страницу)
function displayStoreProducts(minPrice, maxPrice, sortOption) {
  const resultsContainer = document.getElementById("results");
  resultsContainer.innerHTML = "";
  let storesFound = false;
  const itemsPerPage = 6;
  
  // Проходим по каждому магазину в глобальных данных
  for (let store in globalData) {
    if (!Array.isArray(globalData[store])) continue;
    
    // Фильтруем товары данного магазина по цене
    let products = globalData[store].filter(item => item.price >= minPrice && item.price <= maxPrice);
    
    // Применяем сортировку, если выбрана опция
    if (sortOption === "priceAsc") {
      products.sort((a, b) => a.price - b.price);
    } else if (sortOption === "priceDesc") {
      products.sort((a, b) => b.price - a.price);
    }
    
    if (products.length === 0) continue;
    storesFound = true;
    
    // Определяем текущую страницу для данного магазина
    let currentPage = storePages.hasOwnProperty(store) ? storePages[store] : 0;
    const startIndex = currentPage * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageProducts = products.slice(startIndex, endIndex);
    
    // Создаем заголовок магазина, который будет выводиться строго от левого края
    const storeHeading = document.createElement("h2");
    storeHeading.classList.add("store-heading");
    storeHeading.textContent = getStoreName(store);
    resultsContainer.appendChild(storeHeading);
    
    // Создаем горизонтальный контейнер для карточек товаров данного магазина
    const storeRow = document.createElement("div");
    storeRow.classList.add("store-row");
    // Убедимся, что отступы слева отсутствуют – карточки начинаются с самого края
    
    // Если текущая страница не первая, добавляем навигационную карточку с символом "←"
    if (currentPage > 0) {
      const backCard = createNavCard("←", () => {
        storePages[store] = currentPage - 1;
        displayStoreProducts(minPrice, maxPrice, sortOption);
      });
      storeRow.appendChild(backCard);
    }
    
    // Добавляем карточки товаров текущей страницы
    pageProducts.forEach(product => {
      // Пропускаем товары без обязательных данных
      if (!product.name || !product.link) return;
      const card = createProductCard(product);
      storeRow.appendChild(card);
    });
    
    // Если существуют товары для следующей страницы, добавляем навигационную карточку "＋"
    if (endIndex < products.length) {
      const plusCard = createNavCard("＋", () => {
        storePages[store] = currentPage + 1;
        displayStoreProducts(minPrice, maxPrice, sortOption);
      });
      storeRow.appendChild(plusCard);
    }
    
    resultsContainer.appendChild(storeRow);
  }
  
  if (!storesFound) {
    resultsContainer.innerHTML = "<p>Товары не найдены.</p>";
  }
}

// Функция для создания навигационной карточки («＋» или «←»)
function createNavCard(symbol, onClick) {
  const card = document.createElement("div");
  card.classList.add("nav-card");
  card.textContent = symbol;
  card.addEventListener("click", onClick);
  return card;
}

// Функция для создания карточки товара
function createProductCard(product) {
  const card = document.createElement("div");
  card.classList.add("product-card");
  
  const img = document.createElement("img");
  img.src = product.img_url || "placeholder.png";
  img.alt = product.name;
  card.appendChild(img);
  
  const content = document.createElement("div");
  content.classList.add("card-content");
  
  const title = document.createElement("h3");
  title.textContent = product.name;
  content.appendChild(title);
  
  const price = document.createElement("p");
  price.textContent = product.price_display || `${product.price.toFixed(2)} руб.`;
  content.appendChild(price);
  
  if (product.availability) {
    const avail = document.createElement("p");
    avail.textContent = product.availability;
    content.appendChild(avail);
  }
  
  const addBtn = document.createElement("button");
  addBtn.textContent = "Добавить в корзину";
  addBtn.addEventListener("click", () => addToCart(product));
  content.appendChild(addBtn);
  
  card.appendChild(content);
  
  card.addEventListener("dblclick", () => window.open(product.link, "_blank"));
  return card;
}

// Функция преобразования ключа магазина в читаемое имя
function getStoreName(storeKey) {
  const mapping = {
    "gudvin": "Gudvin Group",
    "promispb": "Promispb",
    "hozka": "Hozka.pro",
    "artplast": "ArtPlast",
    "newpackspb": "NewPacksPB",
    "promindus": "Promindus"
  };
  return mapping[storeKey] || storeKey.charAt(0).toUpperCase() + storeKey.slice(1);
}

// Функции работы с корзиной (аналогичные предыдущим версиям)

async function fetchCart() {
  try {
    const response = await fetch("/api/cart");
    const cart = await response.json();
    displayCart(cart);
  } catch (error) {
    console.error("Ошибка получения корзины:", error);
  }
}

function displayCart(cart) {
  const cartContainer = document.getElementById("cart");
  cartContainer.innerHTML = "";
  if (!cart.length) {
    cartContainer.innerHTML = "<p>Корзина пуста.</p>";
    return;
  }
  cart.forEach(item => {
    const cartItem = document.createElement("div");
    cartItem.classList.add("cart-item");
    
    const itemName = document.createElement("span");
    itemName.textContent = item.name;
    cartItem.appendChild(itemName);
    
    const qtyInput = document.createElement("input");
    qtyInput.type = "number";
    qtyInput.value = item.quantity;
    qtyInput.min = 1;
    qtyInput.addEventListener("change", async () => {
      await updateCartItem(item.link, parseInt(qtyInput.value));
      fetchCart();
    });
    cartItem.appendChild(qtyInput);
    
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "Удалить";
    removeBtn.addEventListener("click", async () => {
      await removeCartItem(item.link);
      fetchCart();
    });
    cartItem.appendChild(removeBtn);
    
    document.getElementById("cart").appendChild(cartItem);
  });
}

async function addToCart(product) {
  try {
    const response = await fetch("/api/cart/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product: product })
    });
    const data = await response.json();
    alert(data.message);
    fetchCart();
  } catch (error) {
    console.error("Ошибка при добавлении товара в корзину:", error);
  }
}

async function updateCartItem(link, quantity) {
  try {
    await fetch("/api/cart/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link: link, quantity: quantity })
    });
  } catch (error) {
    console.error("Ошибка обновления товара:", error);
  }
}

async function removeCartItem(link) {
  try {
    await fetch("/api/cart/remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link: link })
    });
  } catch (error) {
    console.error("Ошибка удаления товара:", error);
  }
}

async function checkoutCart() {
  try {
    const response = await fetch("/api/cart/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    const data = await response.json();
    alert(data.message);
    fetchCart();
  } catch (error) {
    console.error("Ошибка при оформлении заказа:", error);
  }
}

// Обработчики событий
document.getElementById("search-form").addEventListener("submit", e => {
  e.preventDefault();
  performSearch();
});
document.getElementById("apply-filters").addEventListener("click", () => performSearch());
document.getElementById("checkout-btn").addEventListener("click", e => {
  e.preventDefault();
  checkoutCart();
});
fetchCart();
