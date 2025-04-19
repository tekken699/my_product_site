// Функция для получения данных корзины с сервера
async function fetchCart() {
    try {
       const response = await fetch("/api/cart");
       const cart = await response.json();
       renderCart(cart);
    } catch (error) {
       console.error("Ошибка получения корзины", error);
    }
}

// Функция для отображения корзины на странице
function renderCart(cart) {
    const cartDiv = document.getElementById("cart");
    cartDiv.innerHTML = "";
    if (cart.length === 0) {
       cartDiv.innerHTML = "<p>Корзина пуста</p>";
       return;
    }

    cart.forEach((item) => {
       const itemDiv = document.createElement("div");
       itemDiv.className = "cart-item";

       // Название товара
       const name = document.createElement("span");
       name.textContent = item.name + " ";
       itemDiv.appendChild(name);

       // Поле ввода количества
       const quantityInput = document.createElement("input");
       quantityInput.type = "number";
       quantityInput.value = item.quantity;
       quantityInput.min = 1;
       quantityInput.dataset.link = item.link;
       itemDiv.appendChild(quantityInput);

       // Кнопка обновления количества
       const updateBtn = document.createElement("button");
       updateBtn.textContent = "Обновить";
       updateBtn.onclick = async function() {
           const newQuantity = +quantityInput.value;
           await updateCartItem(item.link, newQuantity);
           fetchCart();
       };
       itemDiv.appendChild(updateBtn);

       // Кнопка удаления товара из корзины
       const removeBtn = document.createElement("button");
       removeBtn.textContent = "Удалить";
       removeBtn.onclick = async function() {
           await removeCartItem(item.link);
           fetchCart();
       };
       itemDiv.appendChild(removeBtn);

       cartDiv.appendChild(itemDiv);
    });
}

// Функция для обновления количества товара в корзине
async function updateCartItem(link, quantity) {
   try {
      const response = await fetch("/api/cart/update", {
         method: "POST",
         headers: {
           "Content-Type": "application/json"
         },
         body: JSON.stringify({ link: link, quantity: quantity })
      });
      const data = await response.json();
      console.log("Корзина обновлена", data);
   } catch (error) {
      console.error("Ошибка обновления товара", error);
   }
}

// Функция для удаления товара из корзины
async function removeCartItem(link) {
   try {
      const response = await fetch("/api/cart/remove", {
         method: "POST",
         headers: {
           "Content-Type": "application/json"
         },
         body: JSON.stringify({ link: link })
      });
      const data = await response.json();
      console.log("Товар удалён из корзины", data);
   } catch (error) {
      console.error("Ошибка удаления товара", error);
   }
}

// Функция для оформления заказа
async function checkoutCart() {
   try {
      const response = await fetch("/api/cart/checkout", {
         method: "POST",
         headers: {"Content-Type": "application/json"}
      });
      const data = await response.json();
      alert(data.message);
      fetchCart();
   } catch (error) {
      console.error("Ошибка оформления заказа", error);
   }
}

// Привязка обработчика к кнопке оформления заказа
document.getElementById("checkout-btn").addEventListener("click", async function(event) {
   event.preventDefault();
   await checkoutCart();
});

// Обновление корзины при загрузке страницы
window.addEventListener("DOMContentLoaded", fetchCart);
