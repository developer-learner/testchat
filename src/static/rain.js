(function () {
  'use strict';

  var CHARS = 'アイウエオカキクケコサシスセソﾊﾋﾌﾍﾎ0123456789ABCDEF<>/\\|=+*'.split('');
  var canvas = null;
  var ctx = null;
  var rafId = null;
  var drops = [];
  var fontSize = 17;
  var prefersReducedMotion = false;
  var lastTime = 0;
  var colWidth = 0;

  function initCanvas() {
    canvas = document.createElement('canvas');
    canvas.setAttribute('data-testid', 'matrix-rain');
    canvas.style.position = 'fixed';
    canvas.style.inset = '0';
    canvas.style.zIndex = '50';
    canvas.style.opacity = '0.25';
    canvas.style.pointerEvents = 'none';

    document.body.appendChild(canvas);

    ctx = canvas.getContext('2d');
    resizeCanvas();
  }

  function resizeCanvas() {
    if (!canvas) return;
    var w = window.innerWidth;
    var h = window.innerHeight;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.font = 'bold ' + fontSize + 'px "JetBrains Mono", "SF Mono", "Menlo", "Fira Code", monospace';
    colWidth = ctx.measureText('A').width;

    var cols = Math.floor(w / colWidth);
    while (drops.length < cols) {
      drops.push({
        y: Math.random() < 0.6 ? Math.random() * -100 : Math.random() * h / fontSize,
        alpha: 0.3 + Math.random() * 0.7,
        fading: false,
        speed: 0.08 + Math.random() * 0.1,
      });
    }
    if (drops.length > cols) {
      drops.length = cols;
    }
  }

  function draw(ts) {
    if (!ctx || !canvas) return;

    var dt = lastTime ? (ts - lastTime) / 16.67 : 1;
    lastTime = ts;

    ctx.fillStyle = 'rgba(0, 0, 0, 0.025)';
    ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);

    for (var i = 0; i < drops.length; i++) {
      var d = drops[i];
      var text = CHARS[Math.floor(Math.random() * CHARS.length)];
      var x = i * colWidth;
      var y = d.y * fontSize;

      if (!d.fading && Math.random() > 0.995) {
        d.fading = true;
      }

      if (d.fading) {
        d.alpha -= (0.015 + Math.random() * 0.015) * dt;
        if (d.alpha < 0) d.alpha = 0;
      }

      if (d.alpha <= 0 || y > window.innerHeight + 50) {
        d.y = Math.random() < 0.6 ? Math.random() * -100 : Math.random() * (window.innerHeight / fontSize);
        d.alpha = 0.3 + Math.random() * 0.7;
        d.fading = false;
        d.speed = 0.08 + Math.random() * 0.1;
        continue;
      }

      var isHead = Math.random() > 0.975;
      var baseAlpha = isHead ? 0.95 : 0.55;
      var color = isHead
        ? 'rgba(190, 255, 200, ' + (baseAlpha * d.alpha).toFixed(3) + ')'
        : 'rgba(40, 220, 120, ' + (baseAlpha * d.alpha).toFixed(3) + ')';
      ctx.fillStyle = color;
      ctx.fillText(text, x, y);
      ctx.fillText(text, x, y - fontSize);

      d.y += d.speed * dt;
    }
  }

  function loop(ts) {
    draw(ts);
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
