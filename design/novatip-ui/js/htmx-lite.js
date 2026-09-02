/**
 * NovaTIP htmx-lite.js — optional stub
 * Implements data-confirm only (no full HTMX). Local vendor, no CDN.
 */
(function () {
  "use strict";

  document.addEventListener(
    "click",
    function (e) {
      var el = e.target.closest("[data-confirm]");
      if (!el) return;
      var msg = el.getAttribute("data-confirm");
      if (!msg) return;
      if (!window.confirm(msg)) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    },
    true
  );
})();
