/* BlindClock site — EN / zh-Hant switcher.
   Priority: ?lang= param > saved choice > browser language. Defaults to en.
   Pages opt in by tagging content with .lang-en / .lang-zh. */
(function () {
  var STORAGE_KEY = "bc-lang";

  function normalize(value) {
    if (!value) return null;
    value = String(value).toLowerCase();
    if (value.indexOf("zh") === 0) return "zh";
    if (value.indexOf("en") === 0) return "en";
    return null;
  }

  function detect() {
    var fromQuery = normalize(new URLSearchParams(window.location.search).get("lang"));
    if (fromQuery) return fromQuery;
    var saved = null;
    try { saved = normalize(localStorage.getItem(STORAGE_KEY)); } catch (e) {}
    if (saved) return saved;
    var langs = navigator.languages || [navigator.language];
    for (var i = 0; i < langs.length; i++) {
      var lang = normalize(langs[i]);
      if (lang) return lang;
    }
    return "en";
  }

  function apply(lang) {
    document.documentElement.setAttribute("data-lang", lang);
    document.documentElement.setAttribute("lang", lang === "zh" ? "zh-Hant" : "en");
    var buttons = document.querySelectorAll(".lang-switch button");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].classList.toggle("active", buttons[i].getAttribute("data-set-lang") === lang);
    }
  }

  window.bcSetLang = function (lang) {
    lang = normalize(lang) || "en";
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) {}
    apply(lang);
  };

  document.addEventListener("DOMContentLoaded", function () {
    apply(detect());
    var buttons = document.querySelectorAll(".lang-switch button");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener("click", function () {
        window.bcSetLang(this.getAttribute("data-set-lang"));
      });
    }
  });
})();
