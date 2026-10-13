document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".navbar a[href]").forEach(function (link) {
    link.addEventListener("click", function () {
      var menu = link.closest(".navbar-collapse");

      if (menu && menu.classList.contains("show")) {
        var collapse = bootstrap.Collapse.getInstance(menu);

        if (collapse) {
          collapse.hide();
        }
      }
    });
  });
});
