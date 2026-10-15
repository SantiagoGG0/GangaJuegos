/* Ganga Juegos · Panel — interacciones mínimas (vanilla JS). */
(function () {
  'use strict';
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return [].slice.call((r || document).querySelectorAll(s)); }
  function csrf() { var i = $('input[name=csrfmiddlewaretoken]'); return i ? i.value : ''; }
  function cop(v) { return '$ ' + Math.round(v).toLocaleString('es-CO'); }

  // cerrar sesión (Django exige POST)
  $$('[data-logout]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); $('#gjp-logout').submit(); });
  });

  // Ofertas: vista previa del precio con descuento
  var off = $('[data-offer-form]');
  if (off) {
    var sel = $('[data-offer-game]', off), rng = $('[data-offer-pct]', off);
    var upd = function () {
      var opt = sel.options[sel.selectedIndex], pct = +rng.value;
      $('[data-offer-pct-label]', off).textContent = pct + '%';
      $('[data-offer-preview]', off).textContent = opt ? cop(Math.round(+opt.getAttribute('data-prim') * (1 - pct / 100) / 100) * 100) : '—';
    };
    sel.addEventListener('change', upd); rng.addEventListener('input', upd); upd();
  }

  // Cupones: código siempre en mayúsculas
  $$('[data-upper]').forEach(function (i) { i.addEventListener('input', function () { i.value = i.value.toUpperCase(); }); });

  // Carátulas: subir / reemplazar una carátula sin recargar
  var covers = $('[data-covers]');
  if (covers) {
    var file = $('[data-cover-file]', covers), current = null;
    $$('[data-cover-upload]', covers).forEach(function (b) {
      b.addEventListener('click', function () { current = b; file.value = ''; file.click(); });
    });
    file.addEventListener('change', function () {
      if (!file.files.length || !current) return;
      var b = current, card = b.closest('[data-cover-card]'), fd = new FormData();
      fd.append('file', file.files[0]);
      b.textContent = 'Subiendo…'; b.disabled = true;
      fetch(b.getAttribute('data-cover-upload'), { method: 'POST', body: fd, headers: { 'X-CSRFToken': csrf() }, credentials: 'same-origin' })
        .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
        .then(function (d) {
          var img = $('[data-cover-img]', card);
          img.style.background = "#0A2B66 url('" + d.url + "?v=" + Date.now() + "') center/cover no-repeat";
          var miss = $('[data-cover-missing]', img); if (miss) miss.remove();
          b.textContent = 'Reemplazar';
          b.style.border = '1px solid #E6DED2'; b.style.background = 'transparent'; b.style.color = '#011E4F';
        })
        .catch(function () { b.textContent = 'Error · reintentar'; })
        .then(function () { b.disabled = false; });
    });
  }

  // Carga masiva: zona de arrastrar y soltar
  var dz = $('[data-drop-zone]');
  if (dz) {
    var form = dz.closest('form'), input = $('[data-drop-input]', form);
    dz.addEventListener('click', function () { input.click(); });
    input.addEventListener('change', function () { if (input.files.length) form.submit(); });
    ['dragenter', 'dragover'].forEach(function (ev) { dz.addEventListener(ev, function (e) { e.preventDefault(); dz.style.borderColor = '#FC5F01'; }); });
    dz.addEventListener('dragleave', function () { dz.style.borderColor = ''; });
    dz.addEventListener('drop', function (e) {
      e.preventDefault();
      if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; form.submit(); }
    });
  }
})();
