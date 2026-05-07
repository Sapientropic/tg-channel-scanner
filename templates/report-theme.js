(function () {
  var storageKey = "tgcs-report-theme";
  var root = document.documentElement;

  function systemTheme() {
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function storedTheme() {
    try {
      var value = window.localStorage.getItem(storageKey);
      if (value === "light" || value === "dark") {
        return value;
      }
    } catch (error) {
      return null;
    }
    return null;
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    root.style.colorScheme = theme;
    var toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) {
      return;
    }
    var nextTheme = theme === "dark" ? "light" : "dark";
    toggle.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    toggle.setAttribute("aria-label", "Switch to " + nextTheme + " theme");
  }

  function runThemeTransition() {
    root.classList.remove("theme-switching");
    root.offsetWidth;
    root.classList.add("theme-switching");
    window.setTimeout(function () {
      root.classList.remove("theme-switching");
    }, 460);
  }

  function setupScrollCards() {
    var media = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
    var cards = Array.prototype.slice.call(document.querySelectorAll(".job-card, .item-card"));
    var ticking = false;

    if (!cards.length) {
      return;
    }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function clearMotion() {
      root.classList.remove("scroll-motion");
      root.style.removeProperty("--page-parallax-y");
      root.style.removeProperty("--page-parallax-y-reverse");
      cards.forEach(function (card) {
        card.classList.remove("in-scroll-view");
        card.style.removeProperty("--scroll-focus");
        card.style.removeProperty("--scroll-saturate");
        card.style.removeProperty("--scroll-brightness");
        card.style.removeProperty("--scroll-sheen");
        card.style.removeProperty("--scroll-sheen-y");
        card.style.removeProperty("--deck-edge-x");
        card.style.removeProperty("--deck-edge-y");
        card.style.removeProperty("--deck-shadow-x");
        card.style.removeProperty("--deck-shadow-y");
        card.style.removeProperty("--deck-fold-y");
        card.style.removeProperty("--deck-fold-scale");
      });
    }

    function updateCards() {
      if (media && media.matches) {
        clearMotion();
        ticking = false;
        return;
      }

      var viewportHeight = window.innerHeight || document.documentElement.clientHeight || 1;
      var width = window.innerWidth || document.documentElement.clientWidth || 1;
      var motionFactor = width < 520 ? 0.48 : width < 820 ? 0.7 : 1;
      root.classList.add("scroll-motion");
      root.style.setProperty("--page-parallax-y", ((window.scrollY || window.pageYOffset || 0) * -0.07).toFixed(2) + "px");
      root.style.setProperty("--page-parallax-y-reverse", ((window.scrollY || window.pageYOffset || 0) * 0.035).toFixed(2) + "px");

      cards.forEach(function (card) {
        var rect = card.getBoundingClientRect();
        var center = rect.top + rect.height * 0.5;
        var centerOffset = clamp((center - viewportHeight * 0.54) / (viewportHeight * 0.92), -1, 1);
        var entry = clamp((viewportHeight - rect.top) / (viewportHeight + rect.height), 0, 1);
        var focus = 1 - Math.min(1, Math.abs(centerOffset));
        var depth = (8 + focus * 10) * motionFactor;
        var edge = (3 + focus * 2) * motionFactor;
        var fold = centerOffset * -4 * motionFactor;
        var foldScale = 0.82 + focus * 0.42;

        card.style.setProperty("--scroll-focus", focus.toFixed(3));
        card.style.setProperty("--scroll-saturate", (0.94 + focus * 0.08).toFixed(3));
        card.style.setProperty("--scroll-brightness", (0.98 + focus * 0.025).toFixed(3));
        card.style.setProperty("--scroll-sheen", (focus * 0.10).toFixed(3));
        card.style.setProperty("--scroll-sheen-y", ((1 - focus) * 18).toFixed(2) + "px");
        card.style.setProperty("--deck-edge-x", edge.toFixed(2) + "px");
        card.style.setProperty("--deck-edge-y", edge.toFixed(2) + "px");
        card.style.setProperty("--deck-shadow-x", depth.toFixed(2) + "px");
        card.style.setProperty("--deck-shadow-y", depth.toFixed(2) + "px");
        card.style.setProperty("--deck-fold-y", fold.toFixed(2) + "px");
        card.style.setProperty("--deck-fold-scale", foldScale.toFixed(3));
        card.classList.toggle("in-scroll-view", entry > 0.08 && entry < 0.96);
      });

      ticking = false;
    }

    function requestUpdate() {
      if (media && media.matches) {
        clearMotion();
        return;
      }
      root.classList.add("scroll-motion");
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(updateCards);
      }
    }

    if (media && media.matches) {
      clearMotion();
      return;
    }

    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", clearMotion);

    if (media && media.addEventListener) {
      media.addEventListener("change", requestUpdate);
    } else if (media && media.addListener) {
      media.addListener(requestUpdate);
    }
  }

  applyTheme(storedTheme() || systemTheme());

  document.addEventListener("DOMContentLoaded", function () {
    applyTheme(root.getAttribute("data-theme") || systemTheme());

    document.querySelectorAll("[data-theme-toggle]").forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        var current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
        var next = current === "dark" ? "light" : "dark";
        try {
          window.localStorage.setItem(storageKey, next);
        } catch (error) {
          // Theme persistence is a convenience; local files may block storage.
        }
        runThemeTransition();
        applyTheme(next);
      });
    });

    document.querySelectorAll(".raw-toggle").forEach(function (btn) {
      var wrapper = btn.nextElementSibling;
      if (!wrapper) {
        return;
      }
      btn.setAttribute("aria-expanded", wrapper.classList.contains("open") ? "true" : "false");
      btn.addEventListener("click", function () {
        var isOpen = wrapper.classList.toggle("open");
        btn.classList.toggle("open", isOpen);
        btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
        var label = btn.querySelector(".label");
        if (label) {
          label.textContent = isOpen ? "Hide original" : "View original";
        }
      });
    });

    setupScrollCards();
  });
})();
