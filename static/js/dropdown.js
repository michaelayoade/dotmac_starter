/**
 * Dropdown menu fallback for non-Alpine.js contexts.
 * Skipped when Alpine.js is present (Alpine handles its own dropdowns).
 */
document.addEventListener("DOMContentLoaded", function () {
    if (window.Alpine) {
        return;
    }
    var menus = new Map();
    document.querySelectorAll("[data-dropdown-trigger]").forEach(function (trigger) {
        var menuId = trigger.getAttribute("data-dropdown-trigger");
        if (!menuId) {
            return;
        }
        var menu = document.getElementById(menuId);
        if (!menu) {
            return;
        }
        menu.removeAttribute("x-cloak");
        menu.style.display = "none";
        menus.set(menuId, { trigger: trigger, menu: menu });
        trigger.addEventListener("click", function (event) {
            event.stopPropagation();
            var isOpen = menu.style.display !== "none";
            menu.style.display = isOpen ? "none" : "block";
        });
    });
    document.addEventListener("click", function (event) {
        menus.forEach(function (ref) {
            var trigger = ref.trigger;
            var menu = ref.menu;
            if (menu.style.display === "none") {
                return;
            }
            if (menu.contains(event.target) || trigger.contains(event.target)) {
                return;
            }
            menu.style.display = "none";
        });
    });
});
