// Barrierefreiheit: Nach dem Absenden mit Fehlern springt der Fokus auf die Fehlerübersicht.
(function () {
  "use strict";
  var summary = document.getElementById("fehler");
  if (summary) summary.focus();
})();

// Menü: auf breiten Bildschirmen immer offen, auf dem Handy eingeklappt.
// Ohne JavaScript bleibt es ein normales Aufklapp-Menü.
(function () {
  "use strict";
  var wide = window.matchMedia("(min-width: 900px)");
  var targets = [document.getElementById("menu"), document.getElementById("filter-box")];
  function sync() {
    targets.forEach(function (el) {
      if (!el) return;
      if (wide.matches) el.setAttribute("open", "");
      else if (!el.dataset.keepOpen) el.removeAttribute("open");
    });
  }
  sync();
  if (wide.addEventListener) wide.addEventListener("change", sync);
})();
