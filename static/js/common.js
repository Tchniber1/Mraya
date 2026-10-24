// Shared helpers: CSRF-aware fetch, toasts, theme switching.
(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify(body || {}),
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var err = new Error(data.error || "Request failed (" + res.status + ")");
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  function toast(text) {
    var box = document.getElementById("toasts");
    if (!box) return;
    var el = document.createElement("div");
    el.className = "toast glass";
    el.textContent = text;
    box.appendChild(el);
    setTimeout(function () { el.remove(); }, 3800);
  }

  // Apply the theme instantly, then remember it server-side (session + cookie).
  function setTheme(theme) {
    document.body.dataset.theme = theme;
    var form = new FormData();
    form.append("theme", theme);
    fetch("/theme/", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrfToken() },
      body: form,
    }).catch(function () { /* offline: the visual change still applies */ });
  }

  // Server-rendered toasts fade out on their own.
  document.querySelectorAll("#toasts .toast").forEach(function (el) {
    setTimeout(function () { el.remove(); }, 4500);
  });

  window.Mraya = { csrfToken: csrfToken, postJSON: postJSON, toast: toast, setTheme: setTheme };
})();
