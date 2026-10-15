/* Ganga Juegos · motor de efectos (vanilla JS, sin dependencias).
   Todo se activa con atributos data-* para poder llevarlo a las plantillas Django tal cual.
   data-reveal[=rise|left|scale|fade]  aparición al entrar en pantalla (data-delay en ms)
   data-reveal-stagger                 los hijos aparecen en cascada
   data-restagger="clave"              al cambiar la clave, los hijos se re-animan (filtros)
   data-line                           línea de titular que se revela con máscara
   data-shimmer                        degradado que fluye (texto con background-clip)
   data-tilt="grados" [data-holo]      inclinación 3D + brillo que sigue al cursor
   data-magnetic                       botón magnético con destello y onda al clic
   data-pixels                         campo de píxeles de marca (canvas) que reacciona al cursor
   data-spotlight                      expone --mx/--my con la posición del cursor
   data-float                          flotación suave e infinita (hijos o el propio elemento)
   data-marquee                        cinta infinita (contenido duplicado en el HTML)
   data-scroll-progress / data-scroll-header   barra de progreso y sombra del header
   data-pop="valor"                    rebote del número cuando cambia el valor
   data-swap="valor"                   transición cuando cambia el contenido
   data-progress="clave" [data-duration]  barra que se llena (carrusel, toast)
   data-burst="valor"                  explosión de píxeles cuando el valor no está vacío
   data-enter[=drop|toast]             animación al insertarse (menús, toasts, acordeón)
   data-page                           transición entre pantallas
   data-fly + data-fly-img + data-cart-target   la carátula vuela al carrito
   data-intro                          intro con el logo (una vez por sesión)          */
(function () {
  if (window.GangaFX) return;
  var RM = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var EASE = 'cubic-bezier(.2,.8,.2,1)';
  var BRAND = ['#FC3C00', '#FC5F01', '#FC8B01', '#FCC602'];
  var GRAD = 'linear-gradient(90deg,#FC3C00,#FC5F01 35%,#FC8B01 70%,#FCC602)';
  var t0 = performance.now();
  var introUntil = 0;
  var ready = false;
  setTimeout(function () { ready = true; }, 1400);

  function vis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  function introDelay() { return Math.max(0, introUntil - performance.now()); }
  function once(el, k) { if (el['__gj' + k]) return false; el['__gj' + k] = 1; return true; }
  function ensureBox(el) {
    var cs = getComputedStyle(el);
    if (cs.position === 'static') el.style.position = 'relative';
    if (cs.display === 'inline') el.style.display = 'inline-block';
  }

  /* ---------- aparición ---------- */
  function frames(t) {
    if (t === 'fade') return [{ opacity: 0 }, { opacity: 1 }];
    if (t === 'left') return [{ opacity: 0, transform: 'translateX(-28px)' }, { opacity: 1, transform: 'none' }];
    if (t === 'scale') return [{ opacity: 0, transform: 'scale(.94) translateY(16px)' }, { opacity: 1, transform: 'none' }];
    if (t === 'line') return [{ clipPath: 'inset(0 0 100% 0)', transform: 'translateY(45%) skewY(4deg)' }, { clipPath: 'inset(0 0 0 0)', transform: 'none' }];
    return [{ opacity: 0, transform: 'translateY(26px)' }, { opacity: 1, transform: 'none' }];
  }
  function play(el, kf, opts, after) {
    var a = el.animate(kf, Object.assign({ fill: 'both', easing: EASE }, opts));
    a.onfinish = function () { el.style.opacity = ''; el.style.clipPath = ''; a.cancel(); if (after) after(); };
    return a;
  }
  var io = new IntersectionObserver(function (entries) {
    var batch = 0;
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      var el = e.target, d = introDelay();
      el.__gjShown = 1;
      if (el.__gjStag) {
        play(el, frames(el.__gjStag), { duration: 700, delay: d + Math.min(batch++, 10) * 75 });
      } else if (el.hasAttribute('data-line')) {
        play(el, frames('line'), { duration: 900, delay: d + 120 + (+el.getAttribute('data-line') || 0) * 160 });
      } else {
        play(el, frames(el.getAttribute('data-reveal')), { duration: 800, delay: d + (+el.getAttribute('data-delay') || 0) });
      }
    });
  }, { threshold: 0, rootMargin: '0px 0px -3% 0px' });
  function hide(el) {
    if (el.hasAttribute('data-line')) { ensureBox(el); el.style.clipPath = 'inset(0 0 100% 0)'; }
    else el.style.opacity = '0';
    io.observe(el);
    setTimeout(function () { if (!el.__gjShown) { io.unobserve(el); el.__gjShown = 1; el.style.opacity = ''; el.style.clipPath = ''; } }, 3000 + introDelay());
  }
  function reveal(el) {
    if (RM || !once(el, 'rv')) return;
    if (el.hasAttribute('data-reveal-stagger')) {
      var t = el.getAttribute('data-reveal') || 'rise';
      [].slice.call(el.children).forEach(function (k) { if (k.__gjStag) return; k.__gjStag = t; hide(k); });
    } else hide(el);
  }
  function restagger(el) {
    if (RM) return;
    [].slice.call(el.children).slice(0, 16).forEach(function (k, i) {
      k.animate([{ opacity: 0, transform: 'translateY(14px) scale(.97)' }, { opacity: 1, transform: 'none' }],
        { duration: 420, delay: i * 35, easing: EASE, fill: 'backwards' });
    });
  }

  /* ---------- 3D tilt ---------- */
  // Se prepara en la primera interacción (no al cargar): con cientos de
  // tarjetas, medir estilos y crear capas para todas bloqueaba la página.
  function tilt(el) {
    if (RM || !once(el, 'tl')) return;
    var init = function (e) {
      el.removeEventListener('pointerenter', init);
      el.removeEventListener('pointerdown', init);
      setupTilt(el);
      el.dispatchEvent(new PointerEvent(e.type, { bubbles: false, pointerType: e.pointerType, clientX: e.clientX, clientY: e.clientY }));
    };
    el.addEventListener('pointerenter', init);
    el.addEventListener('pointerdown', init);
  }
  function setupTilt(el) {
    ensureBox(el);
    if (getComputedStyle(el).overflow === 'visible') el.style.overflow = 'hidden';
    if (!el.style.isolation) el.style.isolation = 'isolate';
    var max = +el.getAttribute('data-tilt') || 8, holo = el.hasAttribute('data-holo');
    var glare = document.createElement('div');
    glare.setAttribute('aria-hidden', 'true');
    glare.style.cssText = 'position:absolute;inset:0;pointer-events:none;border-radius:inherit;opacity:0;transition:opacity .35s;z-index:5;mix-blend-mode:' + (holo ? 'overlay' : 'soft-light');
    el.appendChild(glare);
    var raf, inside = false;
    el.addEventListener('pointerenter', function (e) {
      if (e.pointerType !== 'mouse') return;
      inside = true;
      var band = document.createElement('div');
      band.style.cssText = 'position:absolute;top:-20%;bottom:-20%;left:0;width:45%;pointer-events:none;z-index:6;background:linear-gradient(100deg,transparent,rgba(255,255,255,.45),transparent)';
      el.appendChild(band);
      band.animate([{ transform: 'translateX(-120%) skewX(-18deg)' }, { transform: 'translateX(320%) skewX(-18deg)' }], { duration: 800, easing: 'cubic-bezier(.4,0,.2,1)' }).onfinish = function () { band.remove(); };
    });
    el.addEventListener('pointermove', function (e) {
      if (e.pointerType !== 'mouse') return;
      var r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(function () {
        if (!inside) return;
        el.style.transition = 'transform .12s ease-out, box-shadow .25s';
        el.style.transform = 'perspective(900px) rotateX(' + ((0.5 - y) * max).toFixed(2) + 'deg) rotateY(' + ((x - 0.5) * max).toFixed(2) + 'deg) translateY(-4px) scale(1.015)';
        glare.style.background = holo
          ? 'linear-gradient(' + (100 + x * 50) + 'deg, transparent 25%, rgba(255,255,255,.75) ' + (35 + y * 20) + '%, rgba(252,198,2,.6) ' + (45 + y * 20) + '%, rgba(53,214,192,.45) ' + (55 + y * 20) + '%, transparent 80%)'
          : 'radial-gradient(circle at ' + (x * 100) + '% ' + (y * 100) + '%, rgba(255,255,255,.7), transparent 55%)';
        glare.style.opacity = '1';
      });
    });
    el.addEventListener('pointerleave', function () {
      inside = false; cancelAnimationFrame(raf);
      el.style.transition = 'transform .7s cubic-bezier(.2,.8,.2,1), box-shadow .25s';
      el.style.transform = '';
      glare.style.opacity = '0';
    });
    el.addEventListener('pointerdown', function (e) { if (e.pointerType !== 'mouse') { el.style.transition = 'transform .15s'; el.style.transform = 'scale(.97)'; } });
    ['pointerup', 'pointercancel'].forEach(function (ev) { el.addEventListener(ev, function (e) { if (e.pointerType !== 'mouse') { el.style.transition = 'transform .5s cubic-bezier(.2,.8,.2,1)'; el.style.transform = ''; } }); });
  }

  /* ---------- botón magnético ---------- */
  function magnetic(el) {
    if (!once(el, 'mg')) return;
    ensureBox(el); el.style.overflow = 'hidden';
    el.addEventListener('pointermove', function (e) {
      if (RM || e.pointerType !== 'mouse') return;
      var r = el.getBoundingClientRect(), x = e.clientX - r.left - r.width / 2, y = e.clientY - r.top - r.height / 2;
      el.style.transition = 'transform .15s ease-out';
      el.style.transform = 'translate(' + (x * 0.12).toFixed(1) + 'px,' + (y * 0.28).toFixed(1) + 'px)';
    });
    el.addEventListener('pointerleave', function () { el.style.transition = 'transform .6s cubic-bezier(.2,.8,.2,1)'; el.style.transform = ''; });
    el.addEventListener('pointerenter', function (e) {
      if (RM || e.pointerType !== 'mouse') return;
      var b = document.createElement('span');
      b.style.cssText = 'position:absolute;top:0;bottom:0;left:0;width:40%;pointer-events:none;background:linear-gradient(100deg,transparent,rgba(255,255,255,.6),transparent)';
      el.appendChild(b);
      b.animate([{ transform: 'translateX(-150%) skewX(-20deg)' }, { transform: 'translateX(380%) skewX(-20deg)' }], { duration: 750, easing: 'cubic-bezier(.4,0,.2,1)' }).onfinish = function () { b.remove(); };
    });
    el.addEventListener('pointerdown', function (e) {
      if (RM) return;
      var r = el.getBoundingClientRect(), s = Math.max(r.width, r.height) * 2.2, d = document.createElement('span');
      d.style.cssText = 'position:absolute;left:' + (e.clientX - r.left - s / 2) + 'px;top:' + (e.clientY - r.top - s / 2) + 'px;width:' + s + 'px;height:' + s + 'px;border-radius:50%;background:rgba(255,255,255,.45);pointer-events:none';
      el.appendChild(d);
      d.animate([{ transform: 'scale(0)', opacity: 0.6 }, { transform: 'scale(1)', opacity: 0 }], { duration: 650, easing: 'cubic-bezier(.2,.8,.2,1)' }).onfinish = function () { d.remove(); };
    });
  }

  /* ---------- campo de píxeles ---------- */
  function pixels(host) {
    if (RM || !once(host, 'px')) return;
    var c = document.createElement('canvas');
    c.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none';
    host.appendChild(c);
    var ctx = c.getContext('2d'), dpr = Math.min(2, window.devicePixelRatio || 1), w = 0, h = 0, parts = [];
    var mx = -9999, my = -9999, tx = 0, ty = 0, px = 0, py = 0, running = false, onScreen = false;
    var density = +host.getAttribute('data-pixels') || 1;
    var SIZES = [3, 4, 5, 6, 8, 10, 14];
    function spawn(init) {
      var s = SIZES[Math.floor(Math.pow(Math.random(), 1.8) * SIZES.length)];
      return { x: Math.random() * w, y: init ? Math.random() * h : h + 20, s: s, z: 0.4 + s / 14,
        vy: -(0.12 + Math.random() * 0.35) * (0.5 + s / 14), vx: (Math.random() - 0.5) * 0.12,
        r: Math.random() * 6.28, vr: (Math.random() - 0.5) * 0.012, c: BRAND[(Math.random() * 4) | 0],
        a: 0.18 + Math.random() * 0.5, tw: Math.random() * 6.28, ox: 0, oy: 0 };
    }
    function resize() {
      var r = host.getBoundingClientRect(); if (!r.width) return;
      w = r.width; h = r.height; c.width = w * dpr; c.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.min(140, Math.round(w * h / 7000 * density));
      parts = []; for (var i = 0; i < n; i++) parts.push(spawn(true));
    }
    var zone = host.closest('[data-spotlight]') || host.parentElement || host;
    zone.addEventListener('pointermove', function (e) {
      var r = host.getBoundingClientRect(); mx = e.clientX - r.left; my = e.clientY - r.top;
      tx = (mx / w - 0.5); ty = (my / h - 0.5);
    });
    zone.addEventListener('pointerleave', function () { mx = my = -9999; tx = ty = 0; });
    function frame(t) {
      if (!onScreen || document.hidden) { running = false; return; }
      px += (tx - px) * 0.05; py += (ty - py) * 0.05;
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        p.x += p.vx; p.y += p.vy; p.r += p.vr;
        var dx = p.x - mx, dy = p.y - my, d2 = dx * dx + dy * dy;
        if (d2 < 16000) { var d = Math.sqrt(d2) || 1, f = (1 - d / 126) * 2.2; p.ox += dx / d * f; p.oy += dy / d * f; }
        p.ox *= 0.94; p.oy *= 0.94;
        if (p.y < -30) { parts[i] = spawn(false); continue; }
        var x = p.x + p.ox - px * 40 * p.z, y = p.y + p.oy - py * 30 * p.z;
        ctx.globalAlpha = p.a * (0.65 + 0.35 * Math.sin(t * 0.0018 + p.tw));
        ctx.fillStyle = p.c;
        ctx.save(); ctx.translate(x, y); ctx.rotate(p.r);
        var s = p.s, rr = Math.min(2, s / 4);
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(-s / 2, -s / 2, s, s, rr); else ctx.rect(-s / 2, -s / 2, s, s);
        ctx.fill(); ctx.restore();
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(frame);
    }
    function start() { if (!running && onScreen) { running = true; requestAnimationFrame(frame); } }
    new IntersectionObserver(function (es) { onScreen = es[0].isIntersecting; if (onScreen) { if (!w) resize(); start(); } }).observe(host);
    if (window.ResizeObserver) new ResizeObserver(resize).observe(host);
    document.addEventListener('visibilitychange', start);
    resize();
  }

  /* ---------- varios ---------- */
  function spotlight(el) {
    if (RM || !once(el, 'sp')) return;
    el.addEventListener('pointermove', function (e) {
      var r = el.getBoundingClientRect();
      el.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      el.style.setProperty('--my', (e.clientY - r.top) + 'px');
    });
  }
  function float(el) {
    if (RM || !once(el, 'fl')) return;
    var kids = el.children.length ? [].slice.call(el.children) : [el];
    kids.forEach(function (k, i) {
      var a = 4 + Math.random() * 8, rot = (Math.random() - 0.5) * 24;
      k.animate([{ transform: 'translate(0,0) rotate(0deg)' }, { transform: 'translate(' + ((Math.random() - 0.5) * 6).toFixed(1) + 'px,' + (-a).toFixed(1) + 'px) rotate(' + rot.toFixed(1) + 'deg)' }],
        { duration: 2200 + Math.random() * 2200, delay: i * 180, direction: 'alternate', iterations: Infinity, easing: 'ease-in-out' });
    });
  }
  function shimmer(el) {
    if (RM || !once(el, 'sh')) return;
    el.animate([{ backgroundPosition: '0% 50%' }, { backgroundPosition: '200% 50%' }], { duration: 5000, iterations: Infinity });
  }
  function marquee(el) {
    if (RM || !once(el, 'mq')) return;
    requestAnimationFrame(function () {
      var a = el.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-50%)' }], { duration: Math.max(12000, el.scrollWidth * 22), iterations: Infinity });
      var z = el.parentElement;
      z.addEventListener('pointerenter', function () { a.updatePlaybackRate ? a.updatePlaybackRate(0.25) : (a.playbackRate = 0.25); });
      z.addEventListener('pointerleave', function () { a.updatePlaybackRate ? a.updatePlaybackRate(1) : (a.playbackRate = 1); });
    });
  }
  function progress(el) {
    if (el.__gjPg) el.__gjPg.cancel();
    el.__gjPg = el.animate([{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], { duration: +el.getAttribute('data-duration') || 5000, easing: 'linear', fill: 'both' });
  }
  function pop(el) {
    if (RM) return; ensureBox(el);
    el.animate([{ transform: 'translateY(50%) scale(.9)', opacity: 0, filter: 'blur(3px)' }, { transform: 'translateY(-6%) scale(1.04)', opacity: 1, filter: 'blur(0)', offset: 0.7 }, { transform: 'none', opacity: 1 }], { duration: 480, easing: EASE });
  }
  function swap(el) {
    if (RM) return;
    el.animate([{ opacity: 0.25, filter: 'saturate(1.8) blur(3px)', clipPath: 'inset(0 0 0 100%)' }, { opacity: 1, filter: 'none', clipPath: 'inset(0 0 0 0)' }], { duration: 700, easing: 'cubic-bezier(.7,0,.2,1)' });
  }
  function enter(el) {
    if (RM) return;
    var t = el.getAttribute('data-enter');
    var kf = t === 'drop' ? [{ opacity: 0, transform: 'translateY(-8px) scale(.98)' }, { opacity: 1, transform: 'none' }]
      : t === 'toast' ? [{ opacity: 0, transform: 'translateY(28px) scale(.94) rotate(-1.5deg)' }, { opacity: 1, transform: 'translateY(-4px) scale(1.01)', offset: 0.7 }, { opacity: 1, transform: 'none' }]
      : [{ opacity: 0, transform: 'translateY(-6px)' }, { opacity: 1, transform: 'none' }];
    el.animate(kf, { duration: t === 'toast' ? 600 : 280, easing: EASE });
  }
  function burst(el, n) {
    if (RM || !el || !vis(el)) return;
    var r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    for (var i = 0; i < (n || 16); i++) {
      var d = document.createElement('div'), s = 4 + Math.random() * 7, a = Math.random() * 6.28, dist = 36 + Math.random() * 70;
      d.style.cssText = 'position:fixed;left:' + cx + 'px;top:' + cy + 'px;width:' + s + 'px;height:' + s + 'px;margin:' + (-s / 2) + 'px 0 0 ' + (-s / 2) + 'px;background:' + BRAND[i % 4] + ';border-radius:1px;pointer-events:none;z-index:99999';
      document.body.appendChild(d);
      d.animate([{ transform: 'translate(0,0) rotate(0)', opacity: 1 }, { transform: 'translate(' + (Math.cos(a) * dist) + 'px,' + (Math.sin(a) * dist + 20) + 'px) rotate(' + (Math.random() * 540) + 'deg)', opacity: 0 }],
        { duration: 650 + Math.random() * 450, easing: 'cubic-bezier(.1,.7,.3,1)' }).onfinish = (function (x) { return function () { x.remove(); }; })(d);
    }
  }
  function strip(node) {
    [node].concat([].slice.call(node.querySelectorAll('*'))).forEach(function (n) {
      [].slice.call(n.attributes).forEach(function (at) { if (at.name.indexOf('data-') === 0) n.removeAttribute(at.name); });
    });
  }
  function fly(btn) {
    if (RM) return;
    var target = [].slice.call(document.querySelectorAll('[data-cart-target]')).filter(vis)[0];
    if (!target) return;
    var scope = btn.closest('[data-fly-scope]') || document;
    var src = [].slice.call(scope.querySelectorAll('[data-fly-img]')).filter(function (x) { return x.getAttribute('data-fly-img') !== '' && vis(x); })[0];
    var r, node;
    if (src) { r = src.getBoundingClientRect(); node = src.cloneNode(true); strip(node); }
    else { var b = btn.getBoundingClientRect(); r = { left: b.left + b.width / 2 - 22, top: b.top + b.height / 2 - 22, width: 44, height: 44 }; node = document.createElement('div'); node.style.background = GRAD; }
    var tr = target.getBoundingClientRect();
    node.style.cssText += ';position:fixed;left:' + r.left + 'px;top:' + r.top + 'px;width:' + r.width + 'px;height:' + r.height + 'px;margin:0;z-index:99998;pointer-events:none;border-radius:8px;overflow:hidden;box-shadow:0 24px 48px -12px rgba(0,0,0,.55);transform:none;opacity:1';
    document.body.appendChild(node);
    var dx = tr.left + tr.width / 2 - (r.left + r.width / 2), dy = tr.top + tr.height / 2 - (r.top + r.height / 2);
    var sc = Math.max(0.06, 26 / Math.max(r.width, r.height));
    node.animate([
      { transform: 'translate(0,0) scale(1) rotate(0)', opacity: 1 },
      { transform: 'translate(0,-14px) scale(1.06) rotate(-4deg)', opacity: 1, offset: 0.15 },
      { transform: 'translate(' + dx * 0.45 + 'px,' + (dy * 0.45 - 110) + 'px) scale(' + ((1 + sc) / 2.2) + ') rotate(-14deg)', opacity: 1, offset: 0.55 },
      { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + sc + ') rotate(10deg)', opacity: 0.7 }
    ], { duration: 950, easing: 'cubic-bezier(.55,0,.25,1)' }).onfinish = function () {
      node.remove();
      target.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.22) rotate(-6deg)' }, { transform: 'scale(.94) rotate(2deg)' }, { transform: 'scale(1)' }], { duration: 520, easing: 'ease-out' });
      burst(target, 14);
    };
  }

  /* ---------- transición entre pantallas ---------- */
  function page(el) {
    if (RM || !ready) return;
    el.animate([
      { opacity: 0, transform: 'translateY(16px)', clipPath: 'polygon(0 0,0 0,-25% 100%,-25% 100%)' },
      { opacity: 1, transform: 'none', clipPath: 'polygon(0 0,125% 0,100% 100%,-25% 100%)' }
    ], { duration: 700, easing: 'cubic-bezier(.7,0,.2,1)' });
    var hdr = document.querySelector('[data-scroll-progress]');
    if (hdr) {
      var line = document.createElement('div');
      line.style.cssText = 'position:absolute;left:0;right:0;bottom:-1px;height:2px;background:' + GRAD + ';transform-origin:0 50%;pointer-events:none;z-index:3';
      hdr.parentElement.appendChild(line);
      line.animate([{ transform: 'scaleX(0)', opacity: 1 }, { transform: 'scaleX(1)', opacity: 1, offset: 0.6 }, { transform: 'scaleX(1)', opacity: 0 }], { duration: 800, easing: 'cubic-bezier(.7,0,.2,1)' }).onfinish = function () { line.remove(); };
    }
  }
  function logo(el) {
    if (RM || !once(el, 'lg')) return;
    var img = el.querySelector('img'), txt = img && img.nextElementSibling, busy = false;
    if (!img) return;
    el.addEventListener('pointerenter', function (e) {
      if (e.pointerType !== 'mouse' || busy) return;
      busy = true;
      img.animate([{ transform: 'rotate(0) scale(1)' }, { transform: 'rotate(-12deg) scale(1.1)', offset: 0.35 }, { transform: 'rotate(5deg) scale(1.04)', offset: 0.7 }, { transform: 'rotate(0) scale(1)' }], { duration: 750, easing: EASE }).onfinish = function () { busy = false; };
      if (txt) txt.animate([{ transform: 'none' }, { transform: 'translateX(3px) skewX(-6deg)', offset: 0.4 }, { transform: 'none' }], { duration: 600, easing: EASE });
      ensureBox(el);
      for (var i = 0; i < 3; i++) {
        var q = document.createElement('span'), s = 4 + i;
        q.style.cssText = 'position:absolute;left:' + (22 + i * 6) + 'px;top:4px;width:' + s + 'px;height:' + s + 'px;border-radius:1px;pointer-events:none;background:' + BRAND[3 - i];
        el.appendChild(q);
        q.animate([{ transform: 'translate(0,0)', opacity: 0 }, { transform: 'translate(' + (4 + i * 3) + 'px,-' + (8 + i * 5) + 'px)', opacity: 1, offset: 0.4 }, { transform: 'translate(' + (8 + i * 4) + 'px,-' + (18 + i * 6) + 'px) rotate(45deg)', opacity: 0 }], { duration: 800, delay: i * 70, easing: EASE, fill: 'both' }).onfinish = (function (x) { return function () { x.remove(); }; })(q);
      }
    });
  }

  /* ---------- intro ---------- */
  function intro(force) {
    var el = document.querySelector('[data-intro]');
    if (!el || RM) return;
    try { if (!force && sessionStorage.getItem('gj-intro')) return; sessionStorage.setItem('gj-intro', '1'); } catch (e) {}
    var frame = el.closest('[data-frame]'); if (frame) frame.scrollTop = 0;
    introUntil = performance.now() + 1900;
    el.style.display = 'block';
    var logo = el.querySelector('[data-intro-logo]'), word = el.querySelector('[data-intro-word]'), box = logo.parentElement;
    logo.animate([{ transform: 'scale(.25) rotate(-28deg)', opacity: 0, filter: 'blur(8px)' }, { transform: 'scale(1.12) rotate(5deg)', opacity: 1, filter: 'blur(0)', offset: 0.6 }, { transform: 'scale(1) rotate(0)', opacity: 1 }], { duration: 950, easing: EASE, fill: 'both' });
    word.animate([{ opacity: 0, transform: 'translateY(24px) skewX(-10deg)', clipPath: 'inset(0 0 100% 0)' }, { opacity: 1, transform: 'none', clipPath: 'inset(0 0 0 0)' }], { duration: 650, delay: 420, easing: EASE, fill: 'both' });
    for (var i = 0; i < 18; i++) {
      var s = 6 + Math.random() * 12, q = document.createElement('div');
      var a = Math.random() * 6.28, R = 160 + Math.random() * 140, ex = (Math.random() - 0.5) * 150, ey = -40 - Math.random() * 90;
      q.style.cssText = 'position:absolute;left:50%;top:50%;width:' + s + 'px;height:' + s + 'px;margin:' + (-s / 2) + 'px 0 0 ' + (-s / 2) + 'px;border-radius:2px;background:' + BRAND[i % 4] + ';pointer-events:none';
      box.appendChild(q);
      q.animate([
        { transform: 'translate(' + Math.cos(a) * R + 'px,' + Math.sin(a) * R + 'px) rotate(200deg)', opacity: 0 },
        { transform: 'translate(' + ex + 'px,' + ey + 'px) rotate(0deg)', opacity: 1, offset: 0.45 },
        { transform: 'translate(' + ex * 1.8 + 'px,' + (ey * 1.6 - 60) + 'px) rotate(-90deg)', opacity: 0 }
      ], { duration: 1600, delay: i * 18, easing: EASE, fill: 'both' }).onfinish = (function (x) { return function () { x.remove(); }; })(q);
    }
    var out = el.animate([{ clipPath: 'polygon(0 0,100% 0,100% 115%,0 100%)' }, { clipPath: 'polygon(0 0,100% 0,100% 0,0 -15%)' }], { duration: 750, delay: 1250, easing: 'cubic-bezier(.75,0,.2,1)', fill: 'forwards' });
    out.onfinish = function () { el.style.display = 'none'; out.cancel(); logo.getAnimations().forEach(function (a) { a.cancel(); }); word.getAnimations().forEach(function (a) { a.cancel(); }); };
  }

  /* ---------- scroll ---------- */
  function scroller(el) {
    var p = el.parentElement;
    while (p && p !== document.body) {
      var oy = getComputedStyle(p).overflowY;
      if ((oy === 'auto' || oy === 'scroll') && p.scrollHeight > p.clientHeight + 1) return p;
      p = p.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  }
  var sRaf;
  function onScroll() {
    cancelAnimationFrame(sRaf);
    sRaf = requestAnimationFrame(function () {
      document.querySelectorAll('[data-scroll-progress]').forEach(function (el) {
        var s = scroller(el), max = s.scrollHeight - s.clientHeight;
        el.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, s.scrollTop / max) : 0).toFixed(4) + ')';
      });
      document.querySelectorAll('[data-scroll-header]').forEach(function (el) {
        el.style.boxShadow = scroller(el).scrollTop > 6 ? '0 12px 32px -14px rgba(0,0,0,.65)' : '';
      });
    });
  }
  document.addEventListener('scroll', onScroll, true);
  window.addEventListener('resize', onScroll);

  /* ---------- contador ---------- */
  var cio = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      cio.unobserve(e.target);
      var el = e.target, to = +el.getAttribute('data-count');
      if (!(to >= 10)) return;
      var orig = [].slice.call(el.childNodes), t1 = performance.now() + introDelay();
      var pre = el.getAttribute('data-prefix') || '', tmp = document.createTextNode('');
      var w = el.getBoundingClientRect().width;
      el.style.minWidth = w + 'px';
      el.replaceChildren(tmp);
      (function step(now) {
        var p = Math.min(1, Math.max(0, (now - t1) / 1600)), v = Math.round(to * (1 - Math.pow(1 - p, 3)));
        tmp.nodeValue = pre + v.toLocaleString('es-CO');
        if (p < 1) requestAnimationFrame(step);
        else { el.replaceChildren.apply(el, orig); el.style.minWidth = ''; }
      })(performance.now());
    });
  }, { threshold: 0 });
  function count(el) { if (RM || !once(el, 'ct')) return; cio.observe(el); }

  /* ---------- registro ---------- */
  var INIT = [
    ['[data-reveal],[data-reveal-stagger],[data-line]', reveal],
    ['[data-tilt]', tilt], ['[data-magnetic]', magnetic], ['[data-pixels]', pixels],
    ['[data-spotlight]', spotlight], ['[data-float]', float], ['[data-logo-hover]', logo], ['[data-shimmer]', shimmer], ['[data-marquee]', marquee], ['[data-count]', count]
  ];
  function each(root, sel, fn) {
    if (root.matches && root.matches(sel)) fn(root);
    if (root.querySelectorAll) [].forEach.call(root.querySelectorAll(sel), fn);
  }
  function scan(root, added) {
    INIT.forEach(function (p) { each(root, p[0], p[1]); });
    each(root, '[data-progress]', progress);
    if (added) {
      each(root, '[data-enter]', enter);
      each(root, '[data-page]', page);
      each(root, '[data-burst]', function (el) { if (ready && el.getAttribute('data-burst')) burst(el); });
    }
    if (!introDone && document.querySelector('[data-intro]')) { introDone = true; intro(false); }
  }
  var introDone = false;
  new MutationObserver(function (muts) {
    muts.forEach(function (m) {
      if (m.type === 'childList') { m.addedNodes.forEach(function (n) { if (n.nodeType === 1) scan(n, true); }); return; }
      var el = m.target, v = el.getAttribute(m.attributeName);
      if (v === m.oldValue) return;
      if (m.attributeName === 'data-pop') pop(el);
      else if (m.attributeName === 'data-swap') swap(el);
      else if (m.attributeName === 'data-progress') progress(el);
      else if (m.attributeName === 'data-restagger') restagger(el);
      else if (m.attributeName === 'data-burst' && v) burst(el);
    });
    onScroll();
  }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeOldValue: true, attributeFilter: ['data-pop', 'data-swap', 'data-progress', 'data-restagger', 'data-burst'] });
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-fly]'); if (b) fly(b); }, true);
  if (document.body) scan(document.body, false);
  document.addEventListener('DOMContentLoaded', function () { scan(document.body, false); });

  window.GangaFX = { intro: function (f) { intro(f !== false); }, burst: burst, refresh: function () { scan(document.body, false); } };
})();
