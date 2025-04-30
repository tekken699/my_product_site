// При загрузке страницы привязываем обработчики на кнопки редактирования
document.addEventListener("DOMContentLoaded", function() {
  const editButtons = document.querySelectorAll(".edit-btn");

  editButtons.forEach(btn => {
    btn.addEventListener("click", function() {
      const field = this.dataset.field;
      const container = this.closest(".editable-field, .data-card");
      const valueSpan = container.querySelector(".field-value");
      const inputField = container.querySelector(".edit-input");
      
      // Если input скрыт – запускаем режим редактирования
      if (!inputField.style.display || inputField.style.display === "none") {
        inputField.value = valueSpan.textContent.trim();
        valueSpan.style.display = "none";
        inputField.style.display = "block";
        inputField.focus();
        inputField.select();
      } else {
        // Иначе завершаем редактирование
        valueSpan.textContent = inputField.value;
        inputField.style.display = "none";
        valueSpan.style.display = "block";
      }
    });
  });

  const editInputs = document.querySelectorAll(".edit-input");
  editInputs.forEach(input => {
    input.addEventListener("blur", function() {
      const container = this.closest(".editable-field, .data-card");
      const valueSpan = container.querySelector(".field-value");
      valueSpan.textContent = this.value;
      this.style.display = "none";
      valueSpan.style.display = "block";
    });
  });
});
