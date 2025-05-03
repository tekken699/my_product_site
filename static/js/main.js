// Глобальные переменные для хранения результатов поиска и текущего номера страницы для каждого магазина
let globalData = null;
let storePages = {}; // Например: { "gudvin": 0, "promispb": 0, ... }
let updateIntervalId = null;

// Функция выполнения поиска: отправляем AJAX-запрос на /api/search
async function performSearch() {
  const query = document.getElementById("search-input").value.trim();
  if (!query) {
    alert("Введите поисковый запрос");
    return;
  }

  // Считываем фильтры: минимальная цена, максимальная и опция сортировки
  const minPrice = parseFloat(document.getElementById("min-price").value) || 0;
  const maxPrice = parseFloat(document.getElementById("max-price").value) || Infinity;
  const sortOption = document.getElementById("sort").value;

  // Отображаем глобальный спиннер по центру экрана с использованием нового Pixel Loader
  document.getElementById("results").innerHTML = `
    <div class="global-spinner">
      <div class="pixel-loader">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
      </div>
    </div>`;

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });
    const data = await response.json();

    // ВАЖНО! Присваиваем данные напрямую, так как сервер возвращает объект с товарами,
    // например: { "gudvin group": [ ... ], "newpackspb": [ ... ] }
    globalData = data;
    
    storePages = {};
    displayStoreProducts(minPrice, maxPrice, sortOption);
    // Запускаем опрос обновлений каждые 3 секунды
    if (updateIntervalId) clearInterval(updateIntervalId);
    updateIntervalId = setInterval(() => pollForUpdates(query, minPrice, maxPrice, sortOption), 3000);
    // Прокручиваем страницу к контейнеру результатов
    document.getElementById("results").scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    console.error("Ошибка запроса:", error);
    document.getElementById("results").innerHTML = "<p>Ошибка загрузки товаров</p>";
  }
}

// Функция опроса обновления результатов
async function pollForUpdates(query, minPrice, maxPrice, sortOption) {
  try {
    const response = await fetch("/api/search/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });
    const updatedData = await response.json();
    // Обновляем глобальные данные, если длина массива товаров для магазина увеличилась
    let updated = false;
    for (let store in updatedData) {
      if (!globalData[store] || 
          !globalData[store].products || 
          globalData[store].products.length < updatedData[store].products.length) {
        globalData[store] = updatedData[store];
        updated = true;
      }
    }
    if (updated) {
      displayStoreProducts(minPrice, maxPrice, sortOption);
      let allReady = true;
      for (let store in globalData) {
        if (!globalData[store].products || globalData[store].products.length === 0)
          allReady = false;
      }
      if (allReady) clearInterval(updateIntervalId);
    }
  } catch (error) {
    console.error("Ошибка обновления:", error);
  }
}


// Функция отображения результатов по магазинам (5 карточек на страницу)
function displayStoreProducts(minPrice, maxPrice, sortOption) {
  const resultsContainer = document.getElementById("results");
  resultsContainer.innerHTML = "";
  let storesFound = false;
  const itemsPerPage = 5;

  for (let store in globalData) {
    // Ожидаем, что globalData[store] имеет структуру { count: number, products: [...] }
    if (!globalData[store] || !globalData[store].products) continue;

    // Фильтрация товаров по цене
    let products = globalData[store].products.filter(item => item.price >= minPrice && item.price <= maxPrice);

    if (sortOption === "availableOnly") {
      products = products.filter(item => {
        if (!item.availability) return false;
        let status = item.availability.trim().toLowerCase();
        return status.includes("в наличии") && !status.startsWith("нет") && !status.includes("под заказ");
      });
    } else if (sortOption === "priceAsc") {
      products.sort((a, b) => a.price - b.price);
    } else if (sortOption === "priceDesc") {
      products.sort((a, b) => b.price - a.price);
    }

    const storeBlock = document.createElement("div");
    storeBlock.classList.add("store-block");

    // Заголовок магазина с названием и количеством товаров
    const storeHeading = document.createElement("h2");
    storeHeading.classList.add("store-heading");
    storeHeading.textContent = `${getStoreName(store)} (${globalData[store].count} товаров)`;
    storeBlock.appendChild(storeHeading);

    // Контейнер для карточек товаров (сетка)
    const productGrid = document.createElement("div");
    productGrid.classList.add("product-grid");

    if (products.length === 0) {
      const spinner = document.createElement("div");
      spinner.innerHTML = `
        <div class="global-spinner">
          <div class="pixel-loader">
            <div></div>
            <div></div>
            <div></div>
            <div></div>
            <div></div>
            <div></div>
            <div></div>
            <div></div>
          </div>
        </div>`;
      productGrid.appendChild(spinner);
    } else {
      let currentPage = storePages.hasOwnProperty(store) ? storePages[store] : 0;
      const startIndex = currentPage * itemsPerPage;
      const endIndex = startIndex + itemsPerPage;
      const pageProducts = products.slice(startIndex, endIndex);

      pageProducts.forEach(product => {
        if (!product.name || !product.link) return;
        product.store = store;
        const card = createProductCard(product);
        productGrid.appendChild(card);
      });
    }
    storeBlock.appendChild(productGrid);

    // Навигация (кнопки "Вперед" и "Назад")
    const navContainer = document.createElement("div");
    navContainer.classList.add("store-nav");

    const nextButton = document.createElement("button");
    nextButton.textContent = "Вперед";
    nextButton.disabled = products.length <= ((storePages[store] || 0) + 1) * itemsPerPage;
    nextButton.addEventListener("click", () => {
      storePages[store] = (storePages[store] || 0) + 1;
      displayStoreProducts(minPrice, maxPrice, sortOption);
    });

    const prevButton = document.createElement("button");
    prevButton.textContent = "Назад";
    prevButton.disabled = (storePages[store] || 0) === 0;
    prevButton.addEventListener("click", () => {
      storePages[store] = (storePages[store] || 0) - 1;
      displayStoreProducts(minPrice, maxPrice, sortOption);
    });

    navContainer.appendChild(nextButton);
    navContainer.appendChild(prevButton);
    storeBlock.appendChild(navContainer);

    resultsContainer.appendChild(storeBlock);
    storesFound = true;
  }

  if (!storesFound) {
    resultsContainer.innerHTML = "<p>Товары не найдены.</p>";
  }
}


// Функция создания карточки товара с быстрыми кнопками для изменения количества
function createProductCard(product) {
  const card = document.createElement("div");
  card.classList.add("product-card");

  // Изображение товара
  const img = document.createElement("img");
  img.src = product.img_url || "placeholder.png";
  img.alt = product.name;
  img.loading = "lazy";
  // Двойной клик по изображению открывает сайт поставщика
  img.addEventListener("dblclick", () => window.open(product.link, "_blank"));
  card.appendChild(img);

  const content = document.createElement("div");
  content.classList.add("card-content");

  // Заголовок товара (наименование)
  const title = document.createElement("h3");
  title.textContent = product.name;
  // Двойной клик по наименованию открывает сайт поставщика
  title.addEventListener("dblclick", () => window.open(product.link, "_blank"));
  content.appendChild(title);

  // Цена товара
  const price = document.createElement("p");
  price.textContent = product.price_display || `${product.price.toFixed(2)} руб.`;
  content.appendChild(price);

  // Отображение статуса наличия
  if (product.availability) {
    const avail = document.createElement("p");
    avail.textContent = product.availability;
    let status = product.availability.trim().toLowerCase();
    if (status.includes("в наличии") && !status.startsWith("нет") && !status.includes("под заказ")) {
      avail.classList.add("status-available");
    } else if (status.includes("под заказ")) {
      avail.classList.add("status-order");
    } else if (status.startsWith("нет")) {
      avail.classList.add("status-unavailable");
    }
    content.appendChild(avail);
  }

  // Кнопка добавления товара в корзину
  const addBtn = document.createElement("button");
  addBtn.textContent = "Добавить в корзину";
  if (product.availability) {
    let status = product.availability.trim().toLowerCase();
    if (status.includes("под заказ") || status.startsWith("нет")) {
      addBtn.disabled = true;
      addBtn.textContent = status.includes("под заказ") ? "Под заказ" : "Нет в наличии";
      addBtn.style.backgroundColor = "#ccc";
      addBtn.style.cursor = "not-allowed";
    }
  }
  addBtn.addEventListener("click", function () {
    if (!this.disabled) {
      let originalText = this.textContent;
      this.textContent = "✓";
      setTimeout(() => {
        this.textContent = originalText;
      }, 1500);
      window.addToCart(product);
      const quickBlock = card.querySelector(".quick-quantity-controls");
      if (quickBlock) quickBlock.style.display = "flex";
    }
  });
  content.appendChild(addBtn);

  // Блок быстрых кнопок для изменения количества товара
  const quickControls = document.createElement("div");
  quickControls.className = "quick-quantity-controls";
  quickControls.style.display = "none";

  // Создаём элемент для отображения количества сразу
  const qtyDisplay = document.createElement("span");
  qtyDisplay.textContent = product.quantity || 1;
  qtyDisplay.className = "quick-qty";

  // Кнопка уменьшения количества
  const minusBtn = document.createElement("button");
  minusBtn.textContent = "–";
  minusBtn.className = "quick-btn";
  minusBtn.addEventListener("click", () => {
    const step = product.step || 1;
    const newQty = Math.max(step, (product.quantity || 1) - step);
    product.quantity = newQty;
    window.updateCartItem && window.updateCartItem(product.link, newQty);
    qtyDisplay.textContent = newQty;
  });
  quickControls.appendChild(minusBtn);

  // Добавляем отображение количества
  quickControls.appendChild(qtyDisplay);

  // Кнопка увеличения количества
  const plusBtn = document.createElement("button");
  plusBtn.textContent = "+";
  plusBtn.className = "quick-btn";
  plusBtn.addEventListener("click", () => {
    const step = product.step || 1;
    const newQty = (product.quantity || 1) + step;
    product.quantity = newQty;
    window.updateCartItem && window.updateCartItem(product.link, newQty);
    qtyDisplay.textContent = newQty;
  });
  quickControls.appendChild(plusBtn);

  content.appendChild(quickControls);
  card.appendChild(content);

  return card;
}

// Функция для преобразования ключа магазина в читаемое имя
function getStoreName(storeKey) {
  const mapping = {
    "gudvin": "Gudvin Group",
    "promispb": "Promispb",
    "hozka": "Hozka.pro",
    "artplast": "ArtPlast",
    "newpackspb": "NewPacksPB",
    "promindus": "Promindus"
  };
  return mapping[storeKey.toLowerCase()] || (storeKey.charAt(0).toUpperCase() + storeKey.slice(1));
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
