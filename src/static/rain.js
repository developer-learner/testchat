(function () {
  'use strict';

  var GLYPHS = [];
  for (var i = 0x30a0; i <= 0x30ff; i++) {
    GLYPHS.push(String.fromCharCode(i));
  }
  for (var j = 0; j <= 9; j++) {
    GLYPHS.push(String(j));
  }

  var canvas = null;
  var ctx = null;
  var rafId = null;
  var columns = [];
  var fontSize = 14;
  var prefersReducedMotion = false;

  function randomGlyph() {
    return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
  }

  function initCanvas() {
    canvas = document.createElement('canvas');
    canvas.setAttribute('data-testid', 'matrix-rain');
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '0';

    document.body.appendChild(canvas);

    ctx = canvas.getContext('2d');
    resizeCanvas();
  }

  function resizeCanvas() {
    if (!canvas) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    var colCount = Math.floor(canvas.width / fontSize);
    while (columns.length < colCount) {
      columns.push({
        y: Math.random() * -100,
        speed: 0.5 + Math.random() * 1.5,
        glyph: randomGlyph(),
      });
    }
    if (columns.length > colCount) {
      columns = columns.slice(0, colCount);
    }

    ctx.font = fontSize + 'px monospace';
  }

  function draw() {
    if (!ctx || !canvas) return;

    ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (var i = 0; i < columns.length; i++) {
      var col = columns[i];

      ctx.fillStyle = '#0f0';
      ctx.fillText(col.glyph, i * fontSize, col.y * fontSize);

      if (col.y > 0) {
        ctx.fillStyle = '#fff';
        ctx.fillText(col.glyph, i * fontSize, (col.y - 1) * fontSize);
      }

      col.y += col.speed;

      if (col.y * fontSize > canvas.height) {
        if (Math.random() > 0.975) {
          col.y = Math.random() * -10;
          col.speed = 0.5 + Math.random() * 1.5;
        } else {
          col.y = -Math.floor(Math.random() * 20);
        }
      }

      if (Math.random() > 0.95) {
        col.glyph = randomGlyph();
      }
    }
  }

  function loop() {
    draw();
    if (!prefersReducedMotion) {
      rafId = requestAnimationFrame(loop);
    }
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      if (rafId !== null && !prefersReducedMotion) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    } else {
      if (rafId === null && !prefersReducedMotion) {
        rafId = requestAnimationFrame(loop);
      }
    }
  }

  function checkReducedMotion() {
    prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function start() {
    checkReducedMotion();

    if (!canvas) {
      initCanvas();
    } else {
      canvas.style.display = 'block';
    }

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('resize', resizeCanvas);

    if (prefersReducedMotion) {
      draw();
    } else {
      rafId = requestAnimationFrame(loop);
    }
  }

  function stop() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }

    document.removeEventListener('visibilitychange', handleVisibilityChange);
    window.removeEventListener('resize', resizeCanvas);

    if (canvas) {
      canvas.style.display = 'none';
    }
  }

  window.MatrixRain = {
    start: function () {
      start();
    },
    stop: function () {
      stop();
    },
  };
})();