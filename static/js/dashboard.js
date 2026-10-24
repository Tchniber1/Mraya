// Dashboard: product status buttons + live XP/level updates.
(function () {
  "use strict";

  function renderProgress(progress) {
    document.getElementById("level-ring").style.setProperty("--pct", progress.progress_pct);
    document.getElementById("level-number").textContent = progress.level;
    document.getElementById("level-title").textContent = progress.title;
    document.getElementById("xp-total").textContent = progress.xp;
    document.getElementById("xp-to-next").textContent = progress.xp_to_next;
    document.getElementById("xp-fill").style.width = progress.progress_pct + "%";
  }

  function updateStartedCount() {
    var el = document.getElementById("count-started");
    if (el) el.textContent = document.querySelectorAll('.product[data-status="started"]').length;
  }

  document.querySelectorAll(".product").forEach(function (card) {
    card.querySelectorAll(".status-group button").forEach(function (button) {
      button.addEventListener("click", function () {
        var status = button.dataset.status;
        if (card.dataset.status === status) return;
        var previousLevel = Number(document.getElementById("level-number").textContent);
        card.setAttribute("aria-busy", "true");

        window.Mraya.postJSON("/dashboard/products/" + card.dataset.product + "/status/", { status: status })
          .then(function (data) {
            card.dataset.status = data.status;
            card.querySelectorAll(".status-group button").forEach(function (b) {
              b.setAttribute("aria-pressed", String(b.dataset.status === data.status));
            });
            renderProgress(data.progress);
            updateStartedCount();
            if (data.xp_gained) window.Mraya.toast("+" + data.xp_gained + " XP");
            if (data.progress.level > previousLevel) {
              window.Mraya.toast("Level up! You are now a " + data.progress.title + " ✦");
            }
          })
          .catch(function (err) {
            if (err.status === 401) { window.location.assign("/accounts/login/"); return; }
            window.Mraya.toast(err.message);
          })
          .finally(function () { card.removeAttribute("aria-busy"); });
      });
    });
  });
})();
