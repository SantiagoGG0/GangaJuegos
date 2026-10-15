(function () {
  'use strict';
  // Eventos del píxel de Meta que se disparan por interacción del usuario
  // (clic en un enlace de WhatsApp, envío de un formulario de pago) —
  // delegados en <body> para cubrir cualquier botón del sitio sin tener que
  // engancharse elemento por elemento.

  // Todo enlace a wa.me dispara "Contact" por defecto. Un enlace puede pedir
  // otro evento con data-pixel-event="Lead"/"InitiateCheckout", y opcionalmente
  // data-pixel-value/-currency para adjuntar el monto (ej. "Comprar por WhatsApp").
  document.addEventListener('click', function (e) {
    if (!window.fbq) return;
    var a = e.target.closest && e.target.closest('a[href^="https://wa.me/"]');
    if (!a) return;
    var name = a.getAttribute('data-pixel-event') || 'Contact';
    var params = {};
    if (a.hasAttribute('data-pixel-value')) {
      params.value = parseFloat(a.getAttribute('data-pixel-value')) || 0;
      params.currency = a.getAttribute('data-pixel-currency') || 'COP';
    }
    fbq('track', name, params);
  }, true);

  // Envío de los formularios de pago (Mercado Pago / PayPal) = inicio de pago.
  document.addEventListener('submit', function (e) {
    if (!window.fbq) return;
    var form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    var action = form.getAttribute('action') || '';
    if (action.indexOf('/carrito/pagar/mercadopago/') === -1 && action.indexOf('/carrito/pagar/paypal/') === -1) return;
    var val = form.getAttribute('data-pixel-value');
    fbq('track', 'InitiateCheckout', val ? { value: parseFloat(val) || 0, currency: 'COP' } : {});
  }, true);
})();
