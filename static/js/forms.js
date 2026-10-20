// Weitere Räume im Formular hinzufügen (Django-Formset). Ohne JavaScript bleibt ein leeres Raumformular.
(function () {
  "use strict";
  var add = document.getElementById("add-room");
  if (!add) return;
  var total = document.getElementById("id_rooms-TOTAL_FORMS");
  var template = document.getElementById("room-template");
  var list = document.getElementById("room-list");
  add.hidden = false;
  add.addEventListener("click", function () {
    var index = parseInt(total.value, 10);
    var html = template.innerHTML.replace(/__prefix__/g, index).replace(/__num__/g, index + 1);
    var wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    list.appendChild(wrapper.firstElementChild);
    total.value = index + 1;
  });
})();
