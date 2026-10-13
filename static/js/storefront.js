document.addEventListener("DOMContentLoaded", function () {
  var cards = Array.from(document.querySelectorAll(".product-card"));
  var tabs = document.querySelectorAll(".category-tab");
  var search = document.getElementById("product-search");
  var favorites = JSON.parse(localStorage.getItem("freshcart-favorites") || "[]");

  function updateProducts() {
    var activeTab = document.querySelector(".category-tab.active");
    var filter = activeTab ? activeTab.dataset.filter : "all";
    var query = search ? search.value.trim().toLowerCase() : "";
    var visible = 0;
    cards.forEach(function (card) {
      var cat = (card.dataset.category || "").trim().toLowerCase();
      var f = (filter || "").trim().toLowerCase();
      var matchesCategory = f === "all" || cat === f || cat.indexOf(f) !== -1 || f.indexOf(cat) !== -1;
      var matchesSearch = !query || (card.dataset.name || "").indexOf(query) !== -1;
      card.hidden = !(matchesCategory && matchesSearch);
      if (!card.hidden) visible += 1;
    });
    var emptyState = document.querySelector(".empty-state");
    if (emptyState) emptyState.hidden = visible !== 0;
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (item) { item.classList.remove("active"); });
      tab.classList.add("active");
      updateProducts();
    });
  });
  if (search) search.addEventListener("input", updateProducts);

  document.querySelectorAll(".favorite-button").forEach(function (button, index) {
    if (favorites.indexOf(index) !== -1) { button.classList.add("saved"); button.textContent = "♥"; }
    button.addEventListener("click", function () {
      var position = favorites.indexOf(index);
      if (position === -1) { favorites.push(index); button.classList.add("saved"); button.textContent = "♥"; }
      else { favorites.splice(position, 1); button.classList.remove("saved"); button.textContent = "♡"; }
      localStorage.setItem("freshcart-favorites", JSON.stringify(favorites));
      document.querySelector(".favorite-count").textContent = favorites.length;
    });
  });
  document.querySelector(".favorite-count").textContent = favorites.length;
});

function subscribeNewsletter(event) {
  event.preventDefault();
  var form = event.currentTarget;
  var button = form.querySelector("button");
  button.innerHTML = "You're on the list <span>✓</span>";
  button.disabled = true;
  return false;
}