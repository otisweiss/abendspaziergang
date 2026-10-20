// Zwei-Klick-Karte: Leaflet und Kartenkacheln werden erst nach Zustimmung geladen.
(function () {
  "use strict";
  var button = document.getElementById("map-load");
  if (!button) return;

  function loadCss(href) {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }

  function loadScript(src, done) {
    var script = document.createElement("script");
    script.src = src;
    script.onload = done;
    document.head.appendChild(script);
  }

  function showMap() {
    var el = document.getElementById("map");
    var points = JSON.parse(document.getElementById("map-points").textContent);
    document.getElementById("map-consent").hidden = true;
    el.hidden = false;
    var map = L.map(el, { scrollWheelZoom: false });
    L.tileLayer(el.dataset.tiles, { maxZoom: 19, attribution: el.dataset.attribution }).addTo(map);
    var bounds = [];
    points.forEach(function (p) {
      var marker = L.marker([p.lat, p.lon]).addTo(map);
      var label = document.createElement(p.url ? "a" : "strong");
      label.textContent = p.name;
      if (p.url) label.href = p.url;
      marker.bindPopup(label);
      bounds.push([p.lat, p.lon]);
    });
    if (bounds.length === 1) map.setView(bounds[0], 16);
    else map.fitBounds(bounds, { padding: [24, 24] });
  }

  button.addEventListener("click", function () {
    var el = document.getElementById("map");
    loadCss(el.dataset.leafletCss);
    loadScript(el.dataset.leafletJs, showMap);
  });
})();
