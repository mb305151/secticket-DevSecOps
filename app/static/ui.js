"use strict";

// Minimal, dependency-free enhancements. Forms and navigation work without JS.
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("app-sidebar");
  const toggle = document.getElementById("sidebar-toggle");
  const backdrop = document.getElementById("sidebar-backdrop");

  function setSidebar(open) {
    if (!sidebar || !toggle || !backdrop) return;
    sidebar.classList.toggle("-translate-x-full", !open);
    backdrop.classList.toggle("hidden", !open);
    toggle.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("overflow-hidden", open);
    if (open) sidebar.querySelector("a")?.focus();
    else toggle.focus();
  }

  toggle?.addEventListener("click", () => setSidebar(true));
  document.querySelectorAll("[data-close-sidebar]").forEach((node) => {
    node.addEventListener("click", () => setSidebar(false));
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && toggle?.getAttribute("aria-expanded") === "true") {
      setSidebar(false);
    }
  });

  document.querySelectorAll("[data-dismiss-flash]").forEach((button) => {
    button.addEventListener("click", () => button.closest(".flash-message")?.remove());
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm");
      if (message && !window.confirm(message)) event.preventDefault();
    });
  });
});
