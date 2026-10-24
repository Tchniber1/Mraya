// Behaviour for ui.css components: dropdown menus, dialogs, tabs, image fallbacks.
(function () {
  "use strict";

  // --- Dropdown menus: [data-menu] > [data-menu-trigger] + [role=menu] -------
  function closeMenu(wrap, focusTrigger) {
    var trigger = wrap.querySelector("[data-menu-trigger]");
    var menu = wrap.querySelector('[role="menu"]');
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    if (focusTrigger) trigger.focus();
  }

  function items(menu) {
    return Array.prototype.slice.call(menu.querySelectorAll('[role="menuitem"]'));
  }

  document.querySelectorAll("[data-menu]").forEach(function (wrap) {
    var trigger = wrap.querySelector("[data-menu-trigger]");
    var menu = wrap.querySelector('[role="menu"]');
    if (!trigger || !menu) return;

    trigger.addEventListener("click", function (event) {
      event.stopPropagation();
      var opening = menu.hidden;
      document.querySelectorAll("[data-menu]").forEach(function (other) { closeMenu(other, false); });
      if (opening) {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        var first = items(menu)[0];
        if (first && event.detail === 0) first.focus(); // keyboard open → focus first item
      }
    });

    menu.addEventListener("keydown", function (event) {
      var list = items(menu);
      var index = list.indexOf(document.activeElement);
      if (event.key === "ArrowDown") { event.preventDefault(); list[(index + 1) % list.length].focus(); }
      if (event.key === "ArrowUp") { event.preventDefault(); list[(index - 1 + list.length) % list.length].focus(); }
      if (event.key === "Home") { event.preventDefault(); list[0].focus(); }
      if (event.key === "End") { event.preventDefault(); list[list.length - 1].focus(); }
      if (event.key === "Tab") closeMenu(wrap, false);
    });
  });

  document.addEventListener("click", function (event) {
    document.querySelectorAll("[data-menu]").forEach(function (wrap) {
      if (!wrap.contains(event.target)) closeMenu(wrap, false);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    document.querySelectorAll("[data-menu]").forEach(function (wrap) { closeMenu(wrap, true); });
  });

  // --- Dialogs: [data-dialog-open="id"] opens <dialog id>, [data-dialog-close] closes ---
  document.querySelectorAll("[data-dialog-open]").forEach(function (opener) {
    var dialog = document.getElementById(opener.dataset.dialogOpen);
    if (!dialog || typeof dialog.showModal !== "function") return;
    opener.addEventListener("click", function () {
      dialog.showModal(); // native modal: focus trap, Esc to close, focus returns to opener
      var cancel = dialog.querySelector("[data-dialog-close]");
      if (cancel) cancel.focus();
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close(); // click on the backdrop
    });
    dialog.querySelectorAll("[data-dialog-close]").forEach(function (button) {
      button.addEventListener("click", function () { dialog.close(); });
    });
  });

  // --- Tabs: [data-tabs] with [role=tab][data-tab] and [data-panel]; "all" shows every panel ---
  document.querySelectorAll("[data-tabs]").forEach(function (root) {
    var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
    var panels = root.querySelectorAll("[data-panel]");

    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
      });
      var key = tab.dataset.tab;
      panels.forEach(function (panel) { panel.hidden = key !== "all" && panel.dataset.panel !== key; });
      if (focus) tab.focus();
    }

    tabs.forEach(function (tab, index) {
      tab.tabIndex = tab.getAttribute("aria-selected") === "true" ? 0 : -1;
      tab.addEventListener("click", function () { select(tab, false); });
      tab.addEventListener("keydown", function (event) {
        if (event.key === "ArrowRight") { event.preventDefault(); select(tabs[(index + 1) % tabs.length], true); }
        if (event.key === "ArrowLeft") { event.preventDefault(); select(tabs[(index - 1 + tabs.length) % tabs.length], true); }
      });
    });
  });

  // --- Remote product images: show the category icon if the image fails -----
  function fallback(img) {
    var icon = img.parentElement && img.parentElement.querySelector(".product-icon");
    img.remove();
    if (icon) icon.hidden = false;
  }
  document.querySelectorAll("img[data-fallback]").forEach(function (img) {
    if (img.complete && img.naturalWidth === 0) fallback(img);
    else img.addEventListener("error", function () { fallback(img); }, { once: true });
  });
})();
