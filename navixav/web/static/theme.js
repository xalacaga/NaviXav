"use strict";

(() => {
  const STORAGE_KEY = "navixav-theme";
  const VALID_PREFERENCES = new Set(["auto", "light", "dark"]);
  const systemTheme = window.matchMedia("(prefers-color-scheme: light)");

  function normalise(preference) {
    return VALID_PREFERENCES.has(preference) ? preference : "auto";
  }

  function getPreference() {
    return normalise(localStorage.getItem(STORAGE_KEY));
  }

  function resolve(preference) {
    const selected = normalise(preference);
    if (selected !== "auto") return selected;
    return systemTheme.matches ? "light" : "dark";
  }

  function apply(preference = getPreference(), persist = false) {
    const selected = normalise(preference);
    const theme = resolve(selected);
    if (persist) localStorage.setItem(STORAGE_KEY, selected);
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.themePreference = selected;
    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.content = theme === "light" ? "#eef2f9" : "#07111f";
    window.dispatchEvent(new CustomEvent("navixav:themechange", {
      detail: { preference: selected, theme },
    }));
  }

  function setPreference(preference) {
    apply(preference, true);
  }

  systemTheme.addEventListener("change", () => {
    if (getPreference() === "auto") apply("auto");
  });

  apply();
  window.THEME = { apply, getPreference, resolve, setPreference };
})();
