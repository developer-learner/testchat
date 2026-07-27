// Draggable sidebar divider.
//
// style.css pins .sidebar to a fixed 250px; sidebar-resize.css hands that
// width to a --sidebar-w custom property so this module can drive it. Width
// is clamped to [MIN, half the viewport] — the CEO's "middle of screen max" —
// and remembered in localStorage across reloads.
window.SidebarResize = (function () {
  var STORE_KEY = 'tc-sidebar-width';
  var MIN_WIDTH = 250;
  var DEFAULT_WIDTH = 250;

  function maxWidth() {
    return Math.round(window.innerWidth / 2);
  }

  function apply(px) {
    var width = Math.max(MIN_WIDTH, Math.min(Math.round(px), maxWidth()));
    document.documentElement.style.setProperty('--sidebar-w', width + 'px');
    return width;
  }

  function store(px) {
    try { localStorage.setItem(STORE_KEY, String(px)); } catch (e) { /* private mode */ }
  }

  function restore() {
    var saved;
    try { saved = parseInt(localStorage.getItem(STORE_KEY), 10); } catch (e) { saved = NaN; }
    if (saved) apply(saved);
  }

  var handle = document.getElementById('sidebar-resizer');
  var sidebar = document.querySelector('.sidebar');
  var dragging = false;

  function onMove(e) {
    if (!dragging || !sidebar) return;
    // Sidebar is the first column, so its left edge is the viewport's — the
    // pointer's x IS the width being requested.
    e.preventDefault();
    apply(e.clientX - sidebar.getBoundingClientRect().left);
  }

  function onUp() {
    if (!dragging) return;
    dragging = false;
    document.body.classList.remove('sidebar-resizing');
    if (sidebar) store(sidebar.getBoundingClientRect().width);
  }

  if (handle) {
    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      dragging = true;
      document.body.classList.add('sidebar-resizing');
    });
    // Double-click the divider to snap back to the default width.
    handle.addEventListener('dblclick', function () {
      store(apply(DEFAULT_WIDTH));
    });
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  // A window that shrank below twice the stored width would otherwise leave
  // the sidebar past the halfway line.
  window.addEventListener('resize', function () {
    if (!sidebar) return;
    apply(sidebar.getBoundingClientRect().width);
  });

  restore();

  return { apply: apply, restore: restore };
})();
