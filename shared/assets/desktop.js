// Панель функций оконного приложения: появляется только внутри pywebview.
(function () {
  "use strict";

  function button(icon, label, handler, mode) {
    var node = document.createElement("button");
    node.className = "icon-btn" + (mode ? " " + mode : "");
    node.type = "button";
    node.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#' + icon + '"></use></svg>' +
      '<span class="label">' + label + "</span>";
    node.addEventListener("click", handler);
    return node;
  }

  function api() {
    return window.pywebview && window.pywebview.api;
  }

  function showAbout(info) {
    var backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML =
      '<div class="modal"><h3>' + info.app + ' v' + info.version + "</h3>" +
      "<p>" + info.stack + "</p>" +
      "<p>Разделов: " + info.sections + ". " + info.note + "</p>" +
      '<div class="actions"><button type="button">Понятно</button></div></div>';
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop || event.target.tagName === "BUTTON") {
        backdrop.remove();
      }
    });
    document.body.appendChild(backdrop);
  }

  function syncTitle() {
    var bridge = api();
    if (bridge && bridge.set_title) {
      bridge.set_title(document.title);
    }
  }

  function build() {
    var bridge = api();
    var bar = document.createElement("div");
    bar.className = "appbar";
    bar.innerHTML =
      '<div class="brand"><div class="brand-mark"><svg class="icon"><use href="#i-logo"></use></svg></div>' +
      '<div><div class="brand-title">ML-кабинет</div><div class="brand-sub">окно приложения</div></div></div>' +
      '<div class="actions"></div>';

    var actions = bar.querySelector(".actions");
    actions.appendChild(button("i-cabinet", "Кабинет", function () { window.location.href = "/"; }));
    actions.appendChild(button("i-refresh", "Обновить", function () { window.location.reload(); }, "accent"));
    actions.appendChild(button("i-external", "В браузере", function () {
      bridge.open_browser(window.location.href);
    }));
    actions.appendChild(button("i-expand", "Полный экран", function () {
      bridge.toggle_fullscreen();
    }));
    actions.appendChild(button("i-info", "О программе", function () {
      bridge.about().then(showAbout);
    }));
    actions.appendChild(button("i-close", "Закрыть", function () {
      bridge.close();
    }, "danger"));

    document.body.insertBefore(bar, document.body.firstChild);
    syncTitle();
  }

  function onKey(event) {
    if (event.key === "F11") {
      event.preventDefault();
      api().toggle_fullscreen();
    }
  }

  document.addEventListener("pywebviewready", function () {
    if (!window.pywebview || !window.pywebview.api) {
      return;
    }
    build();
    document.addEventListener("keydown", onKey);
  });
})();
