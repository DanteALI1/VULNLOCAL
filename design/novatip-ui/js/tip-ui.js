/**
 * NovaTIP tip-ui.js — minimal local alpine-lite behaviour
 * Filters, tabs, description/CVSS toggles, chips. No CDN.
 */
(function () {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }
  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  /* ——— Filter collapse ——— */
  function initFilters(root) {
    qsa("[data-tip-filter]", root).forEach(function (wrap) {
      var toggle = qs("[data-tip-filter-toggle]", wrap);
      if (!toggle) return;
      toggle.addEventListener("click", function (e) {
        e.preventDefault();
        wrap.classList.toggle("is-open");
        var open = wrap.classList.contains("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        var label = qs("[data-tip-filter-label]", toggle);
        if (label) {
          label.textContent = open ? "Скрыть фильтры" : "Показать фильтры";
        }
      });
    });
  }

  /* ——— Tabs (settings etc.) ——— */
  function activateTab(group, name) {
    qsa("[data-tip-tab]", group).forEach(function (btn) {
      var on = btn.getAttribute("data-tip-tab") === name;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    var scope = group.getAttribute("data-tip-tabs") || "";
    var panesRoot = scope
      ? document.querySelector('[data-tip-tab-panes="' + scope + '"]') || group.parentElement
      : group.parentElement;
    qsa("[data-tip-tab-pane]", panesRoot).forEach(function (pane) {
      pane.classList.toggle("is-active", pane.getAttribute("data-tip-tab-pane") === name);
    });
    if (history.replaceState && name) {
      try {
        var url = new URL(window.location.href);
        url.searchParams.set("tab", name);
        history.replaceState(null, "", url.toString());
      } catch (err) {
        /* ignore */
      }
    }
  }

  function initTabs(root) {
    qsa("[data-tip-tabs]", root).forEach(function (group) {
      qsa("[data-tip-tab]", group).forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          if (btn.tagName === "A" && btn.getAttribute("href") && btn.getAttribute("href").charAt(0) === "?") {
            /* allow query navigation; still activate locally for SPA-like feel */
          }
          e.preventDefault();
          activateTab(group, btn.getAttribute("data-tip-tab"));
        });
      });
      var initial =
        group.getAttribute("data-tip-tab-active") ||
        (qs(".tip-tab.is-active", group) && qs(".tip-tab.is-active", group).getAttribute("data-tip-tab")) ||
        (qs("[data-tip-tab]", group) && qs("[data-tip-tab]", group).getAttribute("data-tip-tab"));
      if (initial) activateTab(group, initial);
    });
  }

  /* ——— Segmented toggles (description NVD/BDU, CVSS versions) ——— */
  function initSegments(root) {
    qsa("[data-tip-seg]", root).forEach(function (seg) {
      var targetAttr = seg.getAttribute("data-tip-seg");
      qsa("[data-tip-seg-btn]", seg).forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.preventDefault();
          var val = btn.getAttribute("data-tip-seg-btn");
          qsa("[data-tip-seg-btn]", seg).forEach(function (b) {
            b.classList.toggle("is-active", b === btn);
          });
          if (!targetAttr) return;
          qsa('[data-tip-seg-pane="' + targetAttr + '"]').forEach(function (pane) {
            pane.classList.toggle(
              "is-active",
              pane.getAttribute("data-tip-seg-value") === val
            );
          });
        });
      });
    });
  }

  /* ——— Chips: remove + sync hidden inputs / URL ——— */
  function initChips(root) {
    qsa("[data-tip-chip-remove]", root).forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var chip = btn.closest("[data-tip-chip]");
        var key = btn.getAttribute("data-tip-chip-remove");
        if (chip) chip.remove();
        var form = qs("[data-tip-filter-form]") || qs("form.tip-filter-form");
        if (form && key) {
          qsa('[name="' + key + '"]', form).forEach(function (el) {
            if (el.type === "checkbox" || el.type === "radio") el.checked = false;
            else el.value = "";
          });
        }
        var clearUrl = btn.getAttribute("data-href");
        if (clearUrl) {
          window.location.href = clearUrl;
        }
      });
    });
  }

  /* ——— Confirm forms / buttons (backup for htmx-lite) ——— */
  function initConfirm(root) {
    qsa("[data-confirm]", root).forEach(function (el) {
      el.addEventListener("click", function (e) {
        var msg = el.getAttribute("data-confirm");
        if (msg && !window.confirm(msg)) {
          e.preventDefault();
          e.stopPropagation();
        }
      });
    });
  }

  /* ——— Mobile sidebar hint (optional collapse) ——— */
  function initSidebarToggle(root) {
    var btn = qs("[data-tip-sidebar-toggle]", root);
    var app = qs(".tip-app", root);
    if (!btn || !app) return;
    btn.addEventListener("click", function () {
      app.classList.toggle("is-sidebar-collapsed");
    });
  }

  function init(root) {
    root = root || document;
    initFilters(root);
    initTabs(root);
    initSegments(root);
    initChips(root);
    initConfirm(root);
    initSidebarToggle(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      init(document);
    });
  } else {
    init(document);
  }

  window.TipUI = { init: init, activateTab: activateTab };
})();
