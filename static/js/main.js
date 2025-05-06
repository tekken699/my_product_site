// main.js

document.addEventListener('DOMContentLoaded', function () {
  // Обработчик кнопки "Обновить товары" (для администратора)
  const updateBtn = document.getElementById("update-products-btn");
  if (updateBtn) {
    updateBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        const response = await fetch("/admin/update_products", {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });
        const data = await response.json();
        // Вывод уведомления об успешном запуске обновления товаров
        alert(data.message);
      } catch (error) {
        console.error("Ошибка при обновлении товаров:", error);
        alert("Ошибка обновления товаров");
      }
    });
  }

  // Глобальные переменные
  let globalData = null;
  let storePages = {}; // текущая страница для каждого магазина
  let updateIntervalId = null;
  const itemsPerPage = 5;

  /* ----------- Scroll-to-top functionality ----------- */
  const scrollBtn = document.getElementById('scrollToTop');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
      scrollBtn.classList.add('show');
    } else {
      scrollBtn.classList.remove('show');
    }
  });
  scrollBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  /* ----------- Toast notifications ----------- */
  window.showToast = function (message) {
    const container = document.getElementById('toast-container');
    // Если уже есть уведомление - не добавляем новое
    if (container.childElementCount > 0) return;
    const toast = document.createElement('div');
    toast.classList.add('toast');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3000);
  };

  /* ----------- Поиск и применение фильтров ----------- */
  async function performSearch() {
    const query = document.getElementById("search-input").value.trim();
    if (!query) {
      alert("Введите поисковый запрос");
      return;
    }
    const minPrice = parseFloat(document.getElementById("min-price").value) || 0;
    const maxPrice = parseFloat(document.getElementById("max-price").value) || Infinity;
    const sortOption = document.getElementById("sort").value;
    const availableOnly = document.getElementById("available-only").checked;

    const resultsContainer = document.getElementById("results");
    resultsContainer.innerHTML = `
      <div class="global-spinner">
        <div class="pixel-loader">
          <div></div><div></div><div></div><div></div>
          <div></div><div></div><div></div><div></div>
        </div>
        <p>Загрузка товаров...</p>
      </div>`;

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, availableOnly: availableOnly })
      });
      const data = await response.json();
      globalData = data;
      storePages = {}; // сброс страниц
      displayStoreProducts(minPrice, maxPrice, sortOption);
      
      // Сохранение параметров запроса и результатов в localStorage
      localStorage.setItem("lastSearchQuery", query);
      localStorage.setItem("lastSearchMinPrice", minPrice);
      localStorage.setItem("lastSearchMaxPrice", maxPrice);
      localStorage.setItem("lastSearchSort", sortOption);
      localStorage.setItem("lastSearchAvailable", availableOnly);
      localStorage.setItem("lastSearchData", JSON.stringify(globalData));

      if (updateIntervalId) clearInterval(updateIntervalId);
      updateIntervalId = setInterval(() => pollForUpdates(query, minPrice, maxPrice, sortOption), 3000);
      resultsContainer.scrollIntoView({ behavior: "smooth" });
    } catch (error) {
      console.error("Ошибка запроса:", error);
      resultsContainer.innerHTML = "<p>Ошибка загрузки товаров</p>";
    }
  }

  async function pollForUpdates(query, minPrice, maxPrice, sortOption) {
    try {
      const response = await fetch("/api/search/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      });
      const updatedData = await response.json();
      let updated = false;
      // Если данные для магазина приходят и количество товаров увеличилось – обновляем результат
      for (let store in updatedData) {
        if (updatedData[store].products && updatedData[store].products.length > 0) {
          if (!globalData[store] ||
              !globalData[store].products ||
              globalData[store].products.length < updatedData[store].products.length) {
            globalData[store] = updatedData[store];
            updated = true;
          }
        }
      }
      if (updated) {
        displayStoreProducts(minPrice, maxPrice, sortOption);
        // Обновляем данные в localStorage, чтобы при перезагрузке оставались результаты
        localStorage.setItem("lastSearchData", JSON.stringify(globalData));
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

function displayStoreProducts(minPrice, maxPrice, sortOption) {
  const resultsContainer = document.getElementById("results");
  resultsContainer.innerHTML = "";
  let storesFound = false;
  for (let store in globalData) {
    if (!globalData[store] || !globalData[store].products) continue;
    let products = globalData[store].products.filter(item => item.price >= minPrice && item.price <= maxPrice);
    if (sortOption === "priceAsc") {
      products.sort((a, b) => a.price - b.price);
    } else if (sortOption === "priceDesc") {
      products.sort((a, b) => b.price - a.price);
    }

    const storeBlock = document.createElement("div");
    storeBlock.classList.add("store-block");

    const storeHeading = document.createElement("h2");
    storeHeading.classList.add("store-heading");
    storeHeading.textContent = `${getStoreName(store)} (${globalData[store].count} товаров)`;
    storeBlock.appendChild(storeHeading);

    const productGrid = document.createElement("div");
    productGrid.classList.add("product-grid");

    if (products.length === 0) {
      const spinner = document.createElement("div");
      spinner.innerHTML = `
        <div class="global-spinner">
          <div class="pixel-loader">
            <div></div><div></div><div></div><div></div>
            <div></div><div></div><div></div><div></div>
          </div>
          <p>Загрузка товаров...</p>
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

      // Если общее число товаров меньше 6 – не создаём кнопки
      if (products.length >= 6) {
        setTimeout(() => {
          const firstCard = productGrid.firstElementChild;
          const lastCard = productGrid.lastElementChild;
          if (firstCard && lastCard) {
            const backButton = document.createElement("button");
            backButton.classList.add("pagination-btn", "pagination-prev");
            backButton.textContent = "Назад";
            backButton.disabled = (storePages[store] || 0) === 0;
            const backTop = firstCard.offsetTop + firstCard.offsetHeight / 2;
            backButton.style.position = "absolute";
            backButton.style.left = "-69px"; // смещаем кнопку дальше за пределы карточки
            backButton.style.top = backTop + "px";
            backButton.style.transform = "translateY(-50%)";
            backButton.addEventListener("click", () => {
              storePages[store] = (storePages[store] || 0) - 1;
              displayStoreProducts(minPrice, maxPrice, sortOption);
            });

            const forwardButton = document.createElement("button");
            forwardButton.classList.add("pagination-btn", "pagination-next");
            forwardButton.textContent = "Вперед";
            forwardButton.disabled = products.length <= ((storePages[store] || 0) + 1) * itemsPerPage;
            const forwardTop = lastCard.offsetTop + lastCard.offsetHeight / 2;
            forwardButton.style.position = "absolute";
            forwardButton.style.right = "-99px"; // смещаем кнопку дальше за пределы карточки
            forwardButton.style.top = forwardTop + "px";
            forwardButton.style.transform = "translateY(-50%)";
            forwardButton.addEventListener("click", () => {
              storePages[store] = (storePages[store] || 0) + 1;
              displayStoreProducts(minPrice, maxPrice, sortOption);
            });

            productGrid.appendChild(backButton);
            productGrid.appendChild(forwardButton);
          }
        }, 0);
      }
    }
    storeBlock.appendChild(productGrid);
    resultsContainer.appendChild(storeBlock);
    storesFound = true;
  }
  if (!storesFound) {
    resultsContainer.innerHTML = "<p>Товары не найдены.</p>";
  }
}


  function createProductCard(product) {
    const card = document.createElement("div");
    card.classList.add("product-card");

    const img = document.createElement("img");
    img.src = product.img_url || "placeholder.png";
    img.alt = product.name;
    img.loading = "lazy";
    img.addEventListener("dblclick", () => window.open(product.link, "_blank"));
    card.appendChild(img);

    const content = document.createElement("div");
    content.classList.add("card-content");

    const title = document.createElement("h3");
    title.textContent = product.name;
    title.addEventListener("dblclick", () => window.open(product.link, "_blank"));
    content.appendChild(title);

    const price = document.createElement("p");
    price.textContent = product.price_display || `${parseFloat(product.price).toFixed(2)} руб.`;
    content.appendChild(price);

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
        setTimeout(() => { this.textContent = originalText; }, 1500);
        window.addToCart(product);
        const quickBlock = card.querySelector(".quick-quantity-controls");
        if (quickBlock) quickBlock.style.display = "flex";
      }
    });
    content.appendChild(addBtn);

    const quickControls = document.createElement("div");
    quickControls.className = "quick-quantity-controls";
    quickControls.style.display = "none";
    
    const qtyDisplay = document.createElement("span");
    qtyDisplay.textContent = product.quantity || 1;
    qtyDisplay.className = "quick-qty";
    quickControls.appendChild(qtyDisplay);

    const minusBtn = document.createElement("button");
    minusBtn.textContent = "–";
    minusBtn.className = "quick-btn";
    minusBtn.addEventListener("click", () => {
      const step = product.step || 1;
      const currentQty = product.quantity || 1;
      if (currentQty <= step) {
        window.removeFromCart(product.link, card);
      } else {
        const newQty = currentQty - step;
        product.quantity = newQty;
        if (window.updateCartItem) window.updateCartItem(product.link, newQty);
        qtyDisplay.textContent = newQty;
      }
    });
    quickControls.appendChild(minusBtn);

    const plusBtn = document.createElement("button");
    plusBtn.textContent = "+";
    plusBtn.className = "quick-btn";
    plusBtn.addEventListener("click", () => {
      const step = product.step || 1;
      const newQty = (product.quantity || 1) + step;
      product.quantity = newQty;
      if (window.updateCartItem) window.updateCartItem(product.link, newQty);
      qtyDisplay.textContent = newQty;
    });
    quickControls.appendChild(plusBtn);

    content.appendChild(quickControls);
    card.appendChild(content);
    return card;
  }

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

  /* ----------- Обработчики событий ----------- */
  document.getElementById("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    performSearch();
  });
  document.getElementById("apply-filters").addEventListener("click", (e) => {
    e.preventDefault();
    performSearch();
  });
  const checkoutBtn = document.getElementById("checkout-btn");
  if (checkoutBtn) {
    checkoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      showToast("Переход к оформлению заказа");
      if (window.checkoutCart) window.checkoutCart();
    });
  }

  /* ----------- Функция добавления товара в корзину ----------- */
  window.addToCart = function (product) {
    fetch("/api/cart/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product: product })
    })
      .then(response => response.json())
      .then(data => {
        if (data.message) {
          showToast(data.message);
        }
      })
      .catch(error => {
        console.error("Ошибка добавления в корзину:", error);
        showToast("Ошибка добавления в корзину");
      });
  };

  /* ----------- Функция удаления товара из корзины ----------- */
  window.removeFromCart = function (link, cardElement) {
    fetch("/api/cart/remove", {
      method: 'POST',
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link: link })
    })
      .then(response => response.json())
      .then(data => {
        showToast("Товар удалён из корзины");
        const quickControls = cardElement.querySelector(".quick-quantity-controls");
        if (quickControls) quickControls.style.display = "none";
      })
      .catch(error => {
        console.error("Ошибка при удалении товара из корзины:", error);
        showToast("Ошибка при удалении товара");
      });
  };

  /* ----------- Загрузка сохранённого результата поиска (если есть) ----------- */
  const lastData = localStorage.getItem("lastSearchData");
  if (lastData) {
    globalData = JSON.parse(lastData);
    const lastQuery = localStorage.getItem("lastSearchQuery") || "";
    const lastMin = parseFloat(localStorage.getItem("lastSearchMinPrice")) || 0;
    const lastMax = parseFloat(localStorage.getItem("lastSearchMaxPrice")) || Infinity;
    const lastSort = localStorage.getItem("lastSearchSort") || "default";
    const lastAvail = localStorage.getItem("lastSearchAvailable") === "true";
    document.getElementById("search-input").value = lastQuery;
    document.getElementById("min-price").value = lastMin;
    if (lastMax !== Infinity) document.getElementById("max-price").value = lastMax;
    document.getElementById("sort").value = lastSort;
    document.getElementById("available-only").checked = lastAvail;
    displayStoreProducts(lastMin, lastMax, lastSort);
  }
});
