/* Ganga Juegos · interacciones de la tienda (vanilla JS).
   Reproduce la lógica de estado del prototipo "Ganga Juegos Rediseño v4"
   sobre las plantillas Django. Las animaciones las hace ganga-fx.js a partir
   de los atributos data-* (data-enter, data-pop, data-swap, data-progress,
   data-restagger, data-burst...), por eso aquí basta con cambiar contenido y
   atributos. */
(function () {
  'use strict';

  var NAVY = '#011E4F', NAVY2 = '#0A2B66', CREAM = '#FCF8F3', LINE_D = 'rgba(252,248,243,.25)';
  var GRAD = 'linear-gradient(90deg,#FC3C00,#FC5F01 35%,#FC8B01 70%,#FCC602)';
  var desktopMQ = window.matchMedia('(min-width: 900px)');

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return [].slice.call((root || document).querySelectorAll(sel)); }
  function css(el, styles) { if (el) Object.keys(styles).forEach(function (k) { el.style[k] = styles[k]; }); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function json(id) { var el = document.getElementById(id); if (!el) return null; try { return JSON.parse(el.textContent); } catch (e) { return null; } }
  function store(k, v) { try { if (v === undefined) return sessionStorage.getItem(k); sessionStorage.setItem(k, v); } catch (e) { return null; } }
  function csrf() { var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ''; }

  // mostrar con la animación data-enter: ganga-fx anima los nodos que se
  // insertan en el DOM, así que se re-inserta el elemento en su lugar.
  function show(el) {
    if (!el || !el.hidden) return;
    el.hidden = false;
    if (el.parentNode) el.parentNode.insertBefore(el, el.nextSibling);
  }
  function hide(el) { if (el) el.hidden = true; }

  /* ------------------------------------------------------------ header */
  var panels = { menu: $('[data-panel="menu"]'), search: $('[data-panel="search"]'), curr: $('[data-panel="curr"]') };
  function setOpen(name, open) {
    var p = panels[name]; if (!p) return;
    if (open) show(p); else hide(p);
    $$('[data-toggle="' + name + '"]').forEach(function (b) { b.setAttribute('aria-expanded', open ? 'true' : 'false'); });
  }
  $$('[data-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var name = btn.getAttribute('data-toggle'), p = panels[name];
      var open = p && p.hidden;
      if (name === 'menu') setOpen('search', false);
      if (name === 'search') setOpen('menu', false);
      setOpen(name, open);
      if (name === 'search' && open) { var i = $('input', p); if (i) setTimeout(function () { i.focus(); }, 30); }
    });
  });
  document.addEventListener('click', function (e) {
    if (panels.curr && !panels.curr.hidden && !e.target.closest('[data-curr]')) setOpen('curr', false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    ['curr', 'menu', 'search'].forEach(function (n) { setOpen(n, false); });
    closeMega(true);
  });
  desktopMQ.addEventListener && desktopMQ.addEventListener('change', function () { setOpen('menu', false); setOpen('search', false); closeMega(true); });

  // submenús del menú móvil (Catálogo / Ofertas)
  $$('[data-sub-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var key = btn.getAttribute('data-sub-toggle');
      $$('[data-sub]').forEach(function (s) {
        var t = $('[data-sub-toggle="' + s.getAttribute('data-sub') + '"] [data-sub-chev]');
        var open = s.getAttribute('data-sub') === key && s.hidden;
        if (open) show(s); else hide(s);
        if (t) t.textContent = open ? '−' : '+';
      });
    });
  });

  // mega menús de escritorio (hover con 180 ms de gracia, igual al diseño)
  var navT, megaOpen = null;
  function openMega(key) {
    clearTimeout(navT);
    if (megaOpen === key) return;
    $$('[data-mega-panel]').forEach(function (p) { if (p.getAttribute('data-mega-panel') === key) show(p); else hide(p); });
    megaOpen = key;
  }
  function closeMega(now) {
    clearTimeout(navT);
    var f = function () { $$('[data-mega-panel]').forEach(hide); megaOpen = null; };
    if (now === true) f(); else navT = setTimeout(f, 180);
  }
  $$('[data-mega-trigger]').forEach(function (el) {
    el.addEventListener('mouseenter', function () { if (desktopMQ.matches) openMega(el.getAttribute('data-mega-trigger')); });
    el.addEventListener('mouseleave', closeMega);
  });
  $$('[data-mega-close]').forEach(function (el) { el.addEventListener('mouseenter', function () { closeMega(); }); });
  $$('[data-mega-panel]').forEach(function (p) {
    p.addEventListener('mouseenter', function () { clearTimeout(navT); });
    p.addEventListener('mouseleave', closeMega);
  });

  /* ------------------------------------------------- búsqueda sugerida */
  $$('[data-suggest-form]').forEach(function (form) {
    var input = $('[data-suggest-input]', form);
    var box = form.parentElement.querySelector('[data-suggest-box]');
    if (!input || !box) return;
    var withPlat = box.hasAttribute('data-suggest-plat'), t, seq = 0;
    function render(list) {
      if (!list.length) { hide(box); return; }
      box.innerHTML = list.map(function (s) {
        return '<a href="' + esc(s.url) + '" class="hv-cream" style="display:flex;align-items:center;gap:12px;padding:8px;border-radius:4px;cursor:pointer;color:#011E4F">' +
          '<div style="width:30px;height:40px;border-radius:2px;flex-shrink:0;' + esc(s.cover) + '"></div>' +
          (withPlat
            ? '<div style="flex:1;min-width:0"><div style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(s.title) + '</div><div style="font-size:11px;font-weight:700;letter-spacing:.06em;color:#4A5A78">' + esc(s.plat) + '</div></div>'
            : '<div style="flex:1;min-width:0;font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(s.title) + '</div>') +
          '<div style="font-weight:800;font-size:14px">' + esc(s.from) + '</div></a>';
      }).join('');
      show(box);
    }
    input.addEventListener('input', function () {
      clearTimeout(t);
      var q = input.value.trim();
      if (q.length < 2) { hide(box); return; }
      t = setTimeout(function () {
        var my = ++seq;
        fetch('/buscar/?q=' + encodeURIComponent(q), { headers: { 'X-Requested-With': 'fetch' } })
          .then(function (r) { return r.json(); })
          .then(function (d) { if (my === seq) render((d.results || []).slice(0, 5)); })
          .catch(function () {});
      }, 160);
    });
    input.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(box); });
    document.addEventListener('click', function (e) { if (!box.hidden && !form.contains(e.target) && !box.contains(e.target)) hide(box); });
  });

  /* --------------------------------------------------------- hero home */
  (function () {
    var slides = json('gj-slides'), card = $('[data-hero-card]'), dots = $('[data-hero-dots]');
    if (!slides || !card || !slides.length) return;
    var idx = 0, timer;
    function media(s) {
      if (s.video) return '<video class="gj-hero-video" src="' + esc(s.video) + '"' + (s.image ? ' poster="' + esc(s.image) + '"' : '') + ' autoplay muted loop playsinline preload="metadata"></video>';
      if (s.image) return '<div style="position:absolute;inset:0;background:url(\'' + esc(s.image) + '\') center/cover no-repeat"></div>';
      return '<div style="position:absolute;top:14px;left:14px;font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#8FA3C7">Tráiler en loop · video 16:10</div>';
    }
    function renderDots() {
      $$('[data-hero-dot]', dots).forEach(function (b, i) {
        b.innerHTML = i < idx ? '<span style="position:absolute;inset:0;background:rgba(252,139,1,.5)"></span>'
          : i === idx ? '<span data-progress="s' + idx + '" data-duration="5000" style="position:absolute;inset:0;background:#FC8B01;transform-origin:0 50%"></span>' : '';
      });
    }
    function go(i) {
      idx = (i + slides.length) % slides.length;
      var s = slides[idx];
      card.href = s.url;
      $('[data-hero-media]', card).innerHTML = media(s);
      var disc = $('[data-hero-disc]', card); disc.textContent = s.disc; disc.hidden = !s.disc;
      $('[data-hero-plat]', card).textContent = s.plat;
      $('[data-hero-title]', card).textContent = s.title;
      $('[data-hero-from]', card).textContent = s.from;
      card.setAttribute('data-swap', s.title + '|' + idx);
      renderDots();
    }
    function start() { clearInterval(timer); if (slides.length > 1) timer = setInterval(function () { go(idx + 1); }, 5000); }
    $$('[data-hero-dot]', dots).forEach(function (b) { b.addEventListener('click', function () { go(+b.getAttribute('data-hero-dot')); start(); }); });
    start();
  })();

  /* --------------------------------------------------------- coverflow */
  (function () {
    var data = json('gj-cf'), wrap = $('[data-cf]');
    if (!data || !wrap) return;
    var items = $$('[data-cf-item]', wrap), n = items.length, idx = 0, timer, swiped = false, x0 = null;
    var info = $('[data-cf-info]');
    function layout() {
      var sp = desktopMQ.matches ? 160 : 92;
      items.forEach(function (el, i) {
        var d = i - idx; if (d > n / 2) d -= n; if (d < -n / 2) d += n;
        var a = Math.abs(d);
        el.style.transform = 'translateX(' + (d * sp) + 'px) translateZ(' + (-a * 140) + 'px) rotateY(' + (d === 0 ? 0 : (d > 0 ? -42 : 42)) + 'deg) scale(' + (d === 0 ? 1.06 : 1) + ')';
        el.style.zIndex = String(20 - a);
        el.style.opacity = a > 3 ? '0' : String(1 - a * 0.12);
        el.style.filter = d === 0 ? 'none' : 'brightness(' + (1 - a * 0.2).toFixed(2) + ') saturate(.8)';
      });
      var c = data[idx];
      $('[data-cf-rank]').textContent = c.rank;
      $('[data-cf-plat]').textContent = c.plat;
      $('[data-cf-title]').textContent = c.title;
      $('[data-cf-from]').textContent = c.from;
      $('[data-cf-link]').href = c.url;
      if (info) info.setAttribute('data-swap', c.title);
    }
    function go(i) { idx = (i + n) % n; layout(); }
    function start() { clearInterval(timer); timer = setInterval(function () { go(idx + 1); }, 4500); }
    items.forEach(function (el, i) {
      el.addEventListener('click', function () {
        if (swiped) { swiped = false; return; }
        var d = i - idx; if (d > n / 2) d -= n; if (d < -n / 2) d += n;
        if (d === 0) location.href = data[i].url; else { go(i); start(); }
      });
    });
    $('[data-cf-prev]') && $('[data-cf-prev]').addEventListener('click', function () { go(idx - 1); start(); });
    $('[data-cf-next]') && $('[data-cf-next]').addEventListener('click', function () { go(idx + 1); start(); });
    wrap.addEventListener('pointerdown', function (e) { x0 = e.clientX; });
    wrap.addEventListener('pointerup', function (e) {
      if (x0 == null) return; var dx = e.clientX - x0; x0 = null;
      if (Math.abs(dx) > 30) { swiped = true; setTimeout(function () { swiped = false; }, 60); go(idx + (dx < 0 ? 1 : -1)); start(); }
    });
    desktopMQ.addEventListener && desktopMQ.addEventListener('change', layout);
    layout(); start();
  })();

  /* ------------------------------------------- más vendidos (Todos/PS5/PS4) */
  $$('[data-top-pick]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var key = btn.getAttribute('data-top-pick');
      $$('[data-top-pick]').forEach(function (b) { var on = b === btn; css(b, { background: on ? CREAM : 'transparent', color: on ? NAVY : '#C9D4E8' }); });
      var wrap = $('[data-top-wrap]'), tpl = $('template[data-top="' + key + '"]');
      if (!wrap || !tpl) return;
      var old = $('[data-marquee]', wrap), fresh = old.cloneNode(false);
      fresh.removeAttribute('data-restagger');
      fresh.innerHTML = tpl.innerHTML;
      old.replaceWith(fresh);
      requestAnimationFrame(function () { fresh.setAttribute('data-restagger', key); });
    });
  });

  /* -------------------------------------------------------- acordeones */
  $$('[data-faq]').forEach(function (list) {
    function set(item, open) {
      var b = $('[data-faq-toggle]', item), ic = $('[data-faq-icon]', item), a = $('[data-faq-answer]', item);
      b.style.color = open ? '#FCC602' : CREAM;
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
      css(ic, { background: open ? '#FC8B01' : 'rgba(252,248,243,.1)', color: open ? NAVY : CREAM });
      ic.textContent = open ? '−' : '+';
      if (open) show(a); else hide(a);
    }
    $$('[data-faq-item]', list).forEach(function (item) {
      $('[data-faq-toggle]', item).addEventListener('click', function () {
        var willOpen = $('[data-faq-answer]', item).hidden;
        $$('[data-faq-item]', list).forEach(function (o) { set(o, o === item && willOpen); });
      });
    });
  });

  /* ------------------------------------------------ toast + cupón flotante */
  (function () {
    var host = $('[data-overlays]'); if (!host) return;
    var toast = $('[data-toast]', host), data = json('gj-toast-data');
    var WHEN = ['hace 3 minutos', 'hace 7 minutos', 'hace 12 minutos', 'hace 18 minutos', 'hace 26 minutos', 'hace 41 minutos', 'hace 1 hora'];
    function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
    if (toast && data && data.games && data.games.length && host.getAttribute('data-toast-on') && !store('gj-toast-closed')) {
      var t, last = -1, cover = $('[data-toast-cover]', toast), coverBase = cover.getAttribute('style');
      var count = function () { return +(store('gj-toast-n') || 0); };
      var showToast = function () {
        if (store('gj-toast-closed') || count() >= 6) return;
        var g; do { g = Math.floor(Math.random() * data.games.length); } while (g === last && data.games.length > 1); last = g;
        var place = pick(data.places), game = data.games[g];
        cover.setAttribute('style', coverBase + ';' + game.cover);
        $('[data-toast-flag]', toast).style.background = place.flag;
        $('[data-toast-who]', toast).textContent = pick(data.names) + ' de ' + place.city;
        $('[data-toast-title]', toast).textContent = game.title;
        $('[data-toast-when]', toast).textContent = pick(WHEN);
        store('gj-toast-n', String(count() + 1));
        show(toast);
        $('[data-progress]', toast).setAttribute('data-progress', 't' + count());
        t = setTimeout(function () { hide(toast); t = setTimeout(showToast, 22000 + Math.random() * 26000); }, 6500);
      };
      $('[data-toast-close]', toast).addEventListener('click', function () { clearTimeout(t); hide(toast); store('gj-toast-closed', '1'); });
      t = setTimeout(showToast, 9000);
    }

    var promo = $('[data-promo]', host);
    if (promo && host.getAttribute('data-promo-on') && !store('gj-promo-closed')) {
      var lbl = $('[data-promo-label]', promo), btn = $('[data-promo-copy]', promo), k = 0, pc;
      var setLabel = function () { lbl.textContent = desktopMQ.matches ? lbl.getAttribute('data-long') : lbl.getAttribute('data-short'); };
      setLabel(); desktopMQ.addEventListener && desktopMQ.addEventListener('change', setLabel);
      setTimeout(function () { show(promo); }, 6000);
      btn.addEventListener('click', function () {
        var code = btn.getAttribute('data-promo-copy');
        try { navigator.clipboard.writeText(code); } catch (e) {}
        store('gj-coupon', code);
        lbl.textContent = '¡Copiado!';
        btn.setAttribute('data-burst', 'b' + (++k));
        clearTimeout(pc); pc = setTimeout(setLabel, 2200);
      });
      $('[data-promo-close]', promo).addEventListener('click', function () { hide(promo); store('gj-promo-closed', '1'); });
    }
  })();

  /* ---------------------------------------------------- agregar al carrito */
  function bumpCart(n) {
    $$('[data-cart-count]').forEach(function (el) { el.textContent = n; el.setAttribute('data-pop', n); });
  }
  function addToCart(params, btn) {
    var fd = new FormData();
    Object.keys(params).forEach(function (k) { fd.append(k, params[k]); });
    return fetch('/carrito/agregar/', { method: 'POST', body: fd, headers: { 'X-Requested-With': 'fetch', 'X-CSRFToken': csrf() }, credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        bumpCart(d.cart_count);
        if (window.fbq && d.pixel_event) fbq('track', d.pixel_event.name, d.pixel_event.params || {});
        if (btn) {
          var label = btn.getAttribute('data-label') || btn.textContent;
          btn.setAttribute('data-label', label);
          btn.textContent = 'Agregado ✓';
          clearTimeout(btn.__gjT); btn.__gjT = setTimeout(function () { btn.textContent = label; }, 1600);
        }
        return d;
      });
  }
  $$('[data-add-item]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.getAttribute('data-id'); if (!id) return;
      addToCart({ type: btn.getAttribute('data-add-item'), id: id, acc: btn.getAttribute('data-acc') || '' }, btn)
        .catch(function () { location.href = '/carrito/'; });
    });
  });

  /* ------------------------------------------------------------- detalle */
  (function () {
    var root = $('[data-detail]'); if (!root) return;
    var form = $('[data-add-form]', root), accInput = $('[data-acc-input]', form), acc = 'primaria';
    function select(id) {
      acc = id; accInput.value = id;
      var price = '';
      $$('[data-acc]', root).forEach(function (b) {
        var on = b.getAttribute('data-acc') === id;
        if (on) price = b.getAttribute('data-price');
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
        css(b, { borderColor: on ? '#FC8B01' : 'rgba(252,248,243,.15)', background: on ? CREAM : NAVY2, color: on ? NAVY : CREAM });
        css($('[data-acc-dot]', b), { borderColor: on ? NAVY : 'rgba(252,248,243,.4)', background: on ? NAVY : 'transparent' });
        $('[data-acc-inner]', b).style.background = on ? CREAM : 'transparent';
        $('[data-acc-sub]', b).style.color = on ? '#4A5A78' : '#C9D4E8';
      });
      var p = id === 'primaria';
      $$('[data-col-head]', root).forEach(function (c) { c.style.background = (c.getAttribute('data-col-head') === id) ? '#FCC602' : 'transparent'; });
      $$('[data-col]', root).forEach(function (c) { c.style.background = (c.getAttribute('data-col') === id) ? '#FFEFC7' : 'transparent'; });
      $$('[data-sel-price]', root).forEach(function (el) { el.textContent = price; el.setAttribute('data-pop', price); });
      $$('[data-sel-name]', root).forEach(function (el) { el.textContent = p ? 'Cuenta primaria' : 'Cuenta secundaria'; });
      $$('[data-sel-short]', root).forEach(function (el) { el.textContent = p ? 'Primaria' : 'Secundaria'; });
    }
    $$('[data-acc]', root).forEach(function (b) { b.addEventListener('click', function () { select(b.getAttribute('data-acc')); }); });
    $$('[data-add-cart]', root).forEach(function (btn) {
      btn.setAttribute('data-label', btn.textContent);
      btn.addEventListener('click', function () {
        addToCart({ type: 'juego', id: root.getAttribute('data-id'), acc: acc }, btn).catch(function () { form.submit(); });
      });
    });
    var buy = $('[data-buy-now]', root);
    if (buy) buy.addEventListener('click', function () { form.querySelector('[name=next]').value = 'cart'; form.submit(); });
  })();

  /* ------------------------------------------------------------ catálogo */
  (function () {
    var root = $('[data-catalog]'); if (!root) return;
    // El servidor pinta la primera tanda; el catálogo completo llega como JSON
    // (cacheable) y desde ahí se filtra, ordena y se agregan tandas al hacer scroll.
    var grid = $('[data-grid]', root), more = $('[data-more]', root);
    var BATCH = +root.getAttribute('data-batch') || 48;
    var data = null, list = [], shown = grid.children.length, pending = false;
    var st = { plat: root.getAttribute('data-plat') || 'Todos', genre: root.getAttribute('data-genre') || 'Todos', sort: root.getAttribute('data-sort') || 'Relevancia', deals: !!root.getAttribute('data-deals') };
    var qInput = $('[data-f-query]', root), sortSel = $('[data-f-sort]', root);
    st.q = qInput ? qInput.value.trim() : '';
    var first = true;
    function chip(b, on) {
      if (b.hasAttribute('data-chip')) css(b, { background: on ? '#FC8B01' : 'transparent', color: on ? NAVY : CREAM, borderColor: on ? '#FC8B01' : LINE_D });
      else css(b, { borderLeftColor: on ? '#FC8B01' : 'transparent', color: on ? '#FCC602' : CREAM, fontWeight: on ? '700' : '500' });
    }
    var ROW = 'display:flex;justify-content:space-between;align-items:baseline;gap:4px';
    var LBL = 'font-size:11px;font-weight:600;color:#4A5A78';
    var PRICE = 'font-size:15px;font-weight:800;font-variant-numeric:tabular-nums';
    function card(g) {
      // Mismo marcado que templates/partials/game_card.html
      var cover = g.c
        ? '<div style="position:relative;aspect-ratio:3/4;background:#0A2B66"><img src="' + esc(g.c) + '" alt="" loading="lazy" decoding="async" width="300" height="400" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">'
        : '<div style="position:relative;aspect-ratio:3/4;' + esc(g.bg) + '"><div class="gj-cover-label">' + esc(g.i) + '</div>';
      var disc = g.dp > 0 ? '<span style="position:absolute;top:8px;right:-4px;padding:5px 10px 5px 8px;background:linear-gradient(90deg,#FC3C00,#FC8B01);color:#011E4F;font:italic 900 13px/1 \'Archivo\',sans-serif;transform:skewX(-12deg)">-' + g.dp + '%</span>' : '';
      return '<a href="' + esc(g.u) + '" class="hv-card" data-tilt="10" data-card="1" style="cursor:pointer;display:flex;flex-direction:column;min-width:0;background:#FCF8F3;border-radius:8px;overflow:hidden;color:#011E4F;transition:transform .2s,box-shadow .2s">' +
        cover + disc + '</div>' +
        '<div style="padding:10px 10px 12px;display:flex;flex-direction:column;gap:6px;flex:1">' +
        '<div style="font-size:11px;font-weight:800;letter-spacing:.08em;color:#4A5A78">' + esc(g.p) + '</div>' +
        '<div style="font-size:14px;line-height:18px;font-weight:700;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:36px">' + esc(g.t) + '</div>' +
        '<div style="display:flex;flex-direction:column;gap:2px;margin-top:auto;padding-top:6px;border-top:1px solid #E6DED2">' +
        '<div style="' + ROW + '"><span style="' + LBL + '">Primaria</span><span style="' + PRICE + '">' + esc(g.a) + '</span></div>' +
        '<div style="' + ROW + '"><span style="' + LBL + '">Secundaria</span><span style="' + PRICE + ';color:#C93000">' + esc(g.b) + '</span></div>' +
        '</div></div></a>';
    }
    function filter() {
      var q = st.q.toLowerCase(), g = st.genre.toLowerCase();
      list = data.filter(function (x) {
        return (st.plat === 'Todos' || x.p.indexOf(st.plat) !== -1) &&
          (st.genre === 'Todos' || x.g.indexOf(g) !== -1) &&
          (!st.deals || x.dp > 0) &&
          (!q || x.tl.indexOf(q) !== -1);
      });
      if (st.sort === 'Menor precio') list.sort(function (a, b) { return a.s - b.s || a.r - b.r; });
      else if (st.sort === 'Mayor descuento') list.sort(function (a, b) { return b.dp - a.dp || a.r - b.r; });
    }
    function renderMore() {
      if (!data || shown >= list.length) return;
      grid.insertAdjacentHTML('beforeend', list.slice(shown, shown + BATCH).map(card).join(''));
      shown = Math.min(list.length, shown + BATCH);
      if (more) more.hidden = shown >= list.length;
    }
    if (more) {
      more.addEventListener('click', function (e) { if (data) { e.preventDefault(); renderMore(); } });
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (es) { if (es[0].isIntersecting) renderMore(); }, { rootMargin: '900px 0px' }).observe(more);
      }
    }
    function apply() {
      if (!data) { pending = true; return; }
      filter();
      var n = list.length;
      grid.innerHTML = '';
      shown = 0;
      renderMore();
      if (more) more.hidden = shown >= n;
      $$('[data-result-count]').forEach(function (el) { el.textContent = n; });
      var title = $('[data-catalog-title]', root); if (title) title.textContent = st.deals ? 'Ofertas' : 'Catálogo';
      var banner = $('[data-deals-banner]', root); if (banner) banner.hidden = !st.deals;
      $('[data-no-results]', root).hidden = n > 0;
      $$('[data-f-plat]', root).forEach(function (b) { var on = b.getAttribute('data-f-plat') === st.plat; css(b, { background: on ? CREAM : 'transparent', color: on ? NAVY : '#C9D4E8' }); });
      $$('[data-f-genre]', root).forEach(function (b) { chip(b, b.getAttribute('data-f-genre') === st.genre && !st.deals); });
      $$('[data-f-onlydeals]', root).forEach(function (b) { chip(b, st.deals); });
      $$('[data-nav]').forEach(function (a) {
        var k = a.getAttribute('data-nav'), on = (k === 'deals' && st.deals) || (k === 'catalog' && !st.deals);
        if (k === 'catalog' || k === 'deals') css(a, { color: on ? '#FCC602' : CREAM, borderBottomColor: on ? '#FCC602' : 'transparent' });
      });
      if (!first) {
        grid.setAttribute('data-restagger', [st.plat, st.genre, st.sort, st.deals, st.q].join('|'));
        var p = new URLSearchParams();
        if (st.plat !== 'Todos') p.set('platform', st.plat);
        if (st.genre !== 'Todos') p.set('genre', st.genre);
        if (st.sort !== 'Relevancia') p.set('sort', st.sort);
        if (st.q) p.set('q', st.q);
        var qs = p.toString();
        try { history.replaceState(null, '', (st.deals ? '/ofertas/' : '/catalogo/') + (qs ? '?' + qs : '')); } catch (e) {}
      }
      first = false;
    }
    $$('[data-f-plat]', root).forEach(function (b) { b.addEventListener('click', function () { st.plat = b.getAttribute('data-f-plat'); apply(); }); });
    $$('[data-f-genre]', root).forEach(function (b) { b.addEventListener('click', function () { st.genre = b.getAttribute('data-f-genre'); st.deals = false; apply(); }); });
    $$('[data-f-onlydeals]', root).forEach(function (b) { b.addEventListener('click', function () { st.deals = !st.deals; st.genre = 'Todos'; apply(); }); });
    if (sortSel) sortSel.addEventListener('change', function () { st.sort = sortSel.value; apply(); });
    if (qInput) qInput.addEventListener('input', function () { st.q = qInput.value.trim(); apply(); });
    var clear = $('[data-clear-filters]', root);
    if (clear) clear.addEventListener('click', function (e) { e.preventDefault(); st.plat = 'Todos'; st.genre = 'Todos'; st.deals = false; st.q = ''; if (qInput) qInput.value = ''; apply(); });
    first = false;
    fetch(root.getAttribute('data-src'), { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        d.forEach(function (x, i) { x.r = i; x.tl = x.t.toLowerCase(); });
        data = d;
        if (pending) { apply(); return; }
        // Sin interacción todavía: las tarjetas del servidor ya son la primera tanda.
        filter();
        shown = Math.min(shown, list.length);
        if (more) more.hidden = shown >= list.length;
      })
      .catch(function () { /* sin datos, queda la paginación normal con "Ver más juegos" */ });
  })();

  /* ------------------------------------------------------------- PS Plus */
  (function () {
    var root = $('[data-plus]'), plans = json('gj-plans'); if (!root || !plans) return;
    var tier = root.getAttribute('data-tier'), months = root.getAttribute('data-months');
    var add = $('[data-add-item="plan"]', root);
    function render() {
      $$('[data-tier]', root).forEach(function (b) {
        var t = b.getAttribute('data-tier'), on = t === tier, pl = (plans[t] || {})[months];
        css(b, { borderColor: on ? '#FC8B01' : 'rgba(252,248,243,.15)', background: on ? CREAM : NAVY2, color: on ? NAVY : CREAM });
        $('[data-tier-tag]', b).style.background = on ? '#FCC602' : '#FC8B01';
        css($('[data-tier-per]', b), { color: on ? '#4A5A78' : '#A9B8D6' });
        $('[data-tier-line]', b).style.borderTopColor = on ? '#E6DED2' : 'rgba(252,248,243,.12)';
        if (pl) { $('[data-tier-price]', b).textContent = pl.price; $('[data-tier-per]', b).textContent = pl.per; }
      });
      $$('[data-months]', root).forEach(function (b) {
        if (b === root) return;
        var on = b.getAttribute('data-months') === String(months);
        css(b, { background: on ? CREAM : 'transparent', color: on ? NAVY : '#C9D4E8' });
      });
      var sel = (plans[tier] || {})[months];
      $('[data-plus-summary]', root).textContent = 'PS Plus ' + tier + ' · ' + (months === '1' ? '1 mes' : months + ' meses');
      var price = $('[data-plus-price]', root);
      price.textContent = sel ? sel.price : '—'; price.setAttribute('data-pop', sel ? sel.price : '');
      if (add) add.setAttribute('data-id', sel ? sel.id : '');
    }
    $$('[data-tier]', root).forEach(function (b) { if (b !== root) b.addEventListener('click', function () { tier = b.getAttribute('data-tier'); render(); }); });
    $$('button[data-months]', root).forEach(function (b) { b.addEventListener('click', function () { months = b.getAttribute('data-months'); render(); }); });
  })();

  /* ---------------------------------------------------------- gift cards */
  (function () {
    var root = $('[data-gifts]'); if (!root) return;
    var add = $('[data-add-item="gift"]', root);
    $$('[data-gift]', root).forEach(function (b) {
      b.addEventListener('click', function () {
        $$('[data-gift]', root).forEach(function (o) {
          var on = o === b;
          o.style.borderColor = on ? '#FC8B01' : 'transparent';
          $('[data-fly-img]', o).setAttribute('data-fly-img', on ? '1' : '');
        });
        $('[data-gift-summary]', root).textContent = 'Gift card PSN · USD ' + b.getAttribute('data-amt');
        var price = $('[data-gift-price]', root);
        price.textContent = b.getAttribute('data-price'); price.setAttribute('data-pop', b.getAttribute('data-price'));
        if (add) add.setAttribute('data-id', b.getAttribute('data-gift'));
      });
    });
  })();

  /* ---------------------------------------------------------------- ayuda */
  (function () {
    var root = $('[data-help]'), issues = json('gj-issues'); if (!root || !issues) return;
    $$('[data-issue]', root).forEach(function (b) {
      b.addEventListener('click', function () {
        var key = b.getAttribute('data-issue'), it = issues[key]; if (!it) return;
        $$('[data-issue]', root).forEach(function (o) { var on = o === b; css(o, { borderColor: on ? '#FC5F01' : '#E6DED2', background: on ? '#FFEBDD' : '#fff' }); });
        var msg = $('[data-issue-msg]', root); msg.textContent = '“' + it.msg + '”'; msg.setAttribute('data-swap', key);
        $('[data-issue-link]', root).href = it.link;
      });
    });
  })();

  /* -------------------------------------------------------------- ingresar */
  (function () {
    var root = $('[data-auth]'); if (!root) return;
    $$('[data-auth-tab]', root).forEach(function (b) {
      b.addEventListener('click', function () {
        var tab = b.getAttribute('data-auth-tab'), signup = tab === 'signup';
        $$('[data-auth-tab]', root).forEach(function (o) { var on = o === b; css(o, { background: on ? CREAM : 'transparent', color: on ? NAVY : '#C9D4E8' }); });
        $$('[data-signup-only]', root).forEach(function (el) { el.hidden = !signup; });
        $$('[data-login-only]', root).forEach(function (el) { el.hidden = signup; });
        ['[data-auth-title]', '[data-auth-sub]', '[data-auth-cta]'].forEach(function (s) { var el = $(s, root); el.textContent = el.getAttribute(signup ? 'data-signup' : 'data-login'); });
        $('[data-auth-tab-input]', root).value = tab;
        var pw = $('input[name=password]', root); if (pw) pw.setAttribute('autocomplete', signup ? 'new-password' : 'current-password');
        try { var u = new URL(location.href); u.searchParams.set('tab', tab); history.replaceState(null, '', u); } catch (e) {}
      });
    });
  })();

  /* ------------------------------------------------------------ mi cuenta */
  $$('[data-copy]').forEach(function (b) {
    var label = b.textContent;
    b.addEventListener('click', function () {
      try { navigator.clipboard.writeText(b.getAttribute('data-copy')); } catch (e) {}
      b.textContent = b.getAttribute('data-copied') || 'Copiado ✓';
      setTimeout(function () { b.textContent = label; }, 1500);
    });
  });
  $$('[data-creds-toggle]').forEach(function (b) {
    b.addEventListener('click', function () { var p = b.parentElement.querySelector('[data-creds]'); if (p.hidden) show(p); else hide(p); });
  });

  /* -------------------------------------------------------------- carrito */
  (function () {
    var pays = $$('[data-pay]'); if (!pays.length) return;
    pays.forEach(function (b) {
      b.addEventListener('click', function () {
        var id = b.getAttribute('data-pay');
        pays.forEach(function (o) {
          var on = o === b;
          o.style.borderColor = on ? '#FC8B01' : 'rgba(252,248,243,.15)';
          css($('[data-pay-dot]', o), { borderColor: on ? '#FC8B01' : 'rgba(252,248,243,.4)', background: on ? '#FC8B01' : 'transparent' });
          $('[data-pay-inner]', o).style.background = on ? NAVY : 'transparent';
        });
        $$('[data-pay-go]').forEach(function (g) { g.hidden = g.getAttribute('data-pay-go') !== id; });
      });
    });
    var ref = $('[data-ref-form] input[name=code]');
    if (ref) ref.addEventListener('change', function () { if (ref.value.trim() || ref.defaultValue) ref.form.submit(); });
    var cp = $('[data-coupon-input]'), saved = store('gj-coupon');
    if (cp && !cp.value && saved) cp.value = saved;
  })();
})();
