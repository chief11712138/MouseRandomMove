(() => {
  "use strict";

  const zone = document.getElementById("interactionZone");
  const log = document.getElementById("eventLog");
  const badge = document.getElementById("connectionBadge");
  const focusValue = document.getElementById("focusValue");
  const typedBuffer = document.getElementById("typedBuffer");
  const pointerReadout = document.getElementById("pointerReadout");
  const clearButton = document.getElementById("clearButton");

  const counts = new Map([
    ["mousemove", 0],
    ["click", 0],
    ["wheel", 0],
    ["keydown", 0],
    ["blur", 0],
  ]);

  const counterElements = {
    mousemove: document.getElementById("countMousemove"),
    click: document.getElementById("countClick"),
    wheel: document.getElementById("countWheel"),
    keydown: document.getElementById("countKeydown"),
    blur: document.getElementById("countBlur"),
  };

  let typed = "";
  let lastMouseReport = 0;
  let isActive = false;
  let hasFocus = false;

  function isInsideZone(event) {
    const rect = zone.getBoundingClientRect();
    return event.clientX >= rect.left && event.clientX <= rect.right &&
      event.clientY >= rect.top && event.clientY <= rect.bottom;
  }

  function setFocusState(nextFocus) {
    hasFocus = Boolean(nextFocus);
    focusValue.textContent = hasFocus ? "已获得" : "未获得";
    focusValue.classList.toggle("active", hasFocus);
  }

  function setActive(nextActive) {
    isActive = Boolean(nextActive);
    zone.classList.toggle("is-disabled", !isActive);
    zone.setAttribute("aria-disabled", String(!isActive));
    badge.textContent = isActive ? "运行中，正在接收事件" : "已连接，等待开始";
    badge.className = isActive ? "badge connected" : "badge idle";
    if (!isActive) setFocusState(false);
  }

  async function refreshStatus() {
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const status = await response.json();
      setActive(status.active);
    } catch (error) {
      badge.textContent = "桌面端连接失败";
      badge.className = "badge error";
      isActive = false;
      zone.classList.add("is-disabled");
    }
  }

  async function postEvent(type, details = {}) {
    try {
      const response = await fetch("/api/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, details }),
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      if (result.ignored) refreshStatus();
    } catch (error) {
      badge.textContent = "桌面端连接失败";
      badge.className = "badge error";
    }
  }

  function record(type, details = {}) {
    if (!isActive) return;

    if (counts.has(type)) {
      const next = counts.get(type) + 1;
      counts.set(type, next);
      counterElements[type].textContent = String(next);
    }

    const item = document.createElement("li");
    const time = document.createElement("time");
    time.textContent = new Date().toLocaleTimeString();
    const payload = Object.keys(details).length ? ` ${JSON.stringify(details)}` : "";
    item.append(time, document.createTextNode(`  ${type}${payload}`));
    log.prepend(item);
    while (log.children.length > 60) log.lastElementChild.remove();
    postEvent(type, details);
  }

  document.addEventListener("mousemove", (event) => {
    if (!isInsideZone(event)) return;
    pointerReadout.textContent = `x: ${event.clientX} / y: ${event.clientY}`;
    const now = performance.now();
    if (now - lastMouseReport < 90) return;
    lastMouseReport = now;
    record("mousemove", { x: event.clientX, y: event.clientY });
  }, true);

  document.addEventListener("click", (event) => {
    if (!isInsideZone(event)) return;
    zone.focus({ preventScroll: true });
    setFocusState(true);
    record("click", { x: event.clientX, y: event.clientY, button: event.button });
  }, true);

  document.addEventListener("wheel", (event) => {
    if (!isInsideZone(event)) return;
    event.preventDefault();
    record("wheel", { deltaX: event.deltaX, deltaY: event.deltaY });
  }, { capture: true, passive: false });

  document.addEventListener("keydown", (event) => {
    if (!isActive) return;
    if (event.key.length === 1) {
      typed = (typed + event.key).slice(-80);
      typedBuffer.textContent = typed || "-";
    }
    record("keydown", { key: event.key, code: event.code });
  }, true);

  zone.addEventListener("focus", () => {
    setFocusState(true);
  });

  zone.addEventListener("blur", () => {
    setFocusState(false);
    record("blur");
  });

  clearButton.addEventListener("click", async () => {
    for (const [name] of counts) {
      counts.set(name, 0);
      counterElements[name].textContent = "0";
    }
    typed = "";
    typedBuffer.textContent = "-";
    log.replaceChildren();
    await fetch("/api/reset", { method: "POST", cache: "no-store" });
    refreshStatus();
  });

  setActive(false);
  postEvent("page_ready", {
    userAgent: navigator.userAgent,
    viewport: { width: window.innerWidth, height: window.innerHeight },
  });
  refreshStatus();
  window.setInterval(refreshStatus, 400);
})();
