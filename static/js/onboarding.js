// Home page: gender -> theme, photo previews, form draft memory, loading overlay.
(function () {
  "use strict";

  var form = document.getElementById("onboarding-form");
  if (!form) return;

  var DRAFT_KEY = "mraya:onboarding-draft";
  var DRAFT_FIELDS = ["age", "budget", "currency", "city", "brand_preferences", "style_preferences"];
  var stepForm = document.getElementById("step-form");

  // --- Gender choice switches the whole palette ---------------------------
  form.querySelectorAll('input[name="gender"]').forEach(function (radio) {
    radio.addEventListener("change", function () {
      window.Mraya.setTheme(radio.value);
      stepForm.classList.remove("locked");
      stepForm.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  // --- Photo previews + drag and drop -----------------------------------
  form.querySelectorAll("[data-dropzone]").forEach(function (zone) {
    var input = zone.querySelector('input[type="file"]');
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      var old = zone.querySelector("img");
      if (old) old.remove();
      if (!file) return;
      var img = document.createElement("img");
      img.alt = "Preview";
      img.src = URL.createObjectURL(file);
      zone.appendChild(img);
    });
    ["dragenter", "dragover"].forEach(function (evt) {
      zone.addEventListener(evt, function () { zone.classList.add("dragging"); });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      zone.addEventListener(evt, function () { zone.classList.remove("dragging"); });
    });
  });

  // --- Remember the typed answers in this browser ------------------------
  function readDraft() {
    try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}"); } catch (e) { return {}; }
  }
  function saveDraft() {
    var draft = {};
    DRAFT_FIELDS.forEach(function (name) {
      var el = form.elements[name];
      if (el) draft[name] = el.value;
    });
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch (e) { /* storage blocked */ }
  }
  var draft = readDraft();
  DRAFT_FIELDS.forEach(function (name) {
    var el = form.elements[name];
    if (el && !el.value && draft[name]) el.value = draft[name];
  });
  form.addEventListener("input", saveDraft);

  // --- Client-side checks + loading overlay -------------------------------
  var steps = [
    "Reading proportions and colours",
    "Studying face shape and skin tone",
    "Matching brands to your budget",
    "Finding where to buy nearby",
    "Writing your routine",
  ];

  form.addEventListener("submit", function (event) {
    var gender = form.querySelector('input[name="gender"]:checked');
    var missing = !gender ? "Choose Man or Woman first." :
      !form.elements.full_body.files.length ? "Add your full-body photo." :
      !form.elements.face.files.length ? "Add your face photo." :
      !form.elements.age.value ? "Tell us your age." :
      !form.elements.budget.value ? "Set your budget." :
      !form.querySelector('input[name="interests"]:checked') ? "Pick at least one category." : "";
    if (missing) {
      event.preventDefault();
      window.Mraya.toast(missing);
      return;
    }
    saveDraft();
    document.getElementById("analyze-btn").disabled = true;
    var overlay = document.getElementById("overlay");
    var label = document.getElementById("overlay-step");
    overlay.classList.remove("hidden");
    var i = 0;
    setInterval(function () {
      i = (i + 1) % steps.length;
      label.textContent = steps[i];
    }, 3500);
  });
})();
