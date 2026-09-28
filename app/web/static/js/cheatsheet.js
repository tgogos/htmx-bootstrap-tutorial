/* global bootstrap: false */

(() => {
  "use strict";

  document.querySelectorAll(".tooltip-demo").forEach((tooltip) => {
    new bootstrap.Tooltip(tooltip, {
      selector: "[data-bs-toggle=\"tooltip\"]",
    });
  });

  document.querySelectorAll("[data-bs-toggle=\"popover\"]").forEach((popover) => {
    new bootstrap.Popover(popover);
  });

  document.querySelectorAll(".bd-cheatsheet .toast").forEach((toastNode) => {
    const toast = new bootstrap.Toast(toastNode, {
      autohide: false,
    });
    toast.show();
  });

  document.querySelectorAll(".bd-cheatsheet [href=\"#\"], .bd-cheatsheet [type=\"submit\"]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
    });
  });
})();
