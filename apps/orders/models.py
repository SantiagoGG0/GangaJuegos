import random

from django.conf import settings
from django.db import models


def _new_pedido_ref():
    return f'#GJ-{random.randint(1000, 9999)}'


def _new_reclamo_ref():
    return f'#RC-{random.randint(100, 999)}'


class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('En proceso', 'En proceso'),
        ('Entregado', 'Entregado'),
    ]
    METODO_PAGO_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('mercadopago', 'Mercado Pago'),
        ('paypal', 'PayPal'),
    ]
    PAGO_ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
    ]

    ref = models.CharField('referencia', max_length=20, unique=True, default=_new_pedido_ref)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pedidos')
    fecha = models.DateTimeField('fecha', auto_now_add=True)
    estado = models.CharField('estado', max_length=15, choices=ESTADO_CHOICES, default='En proceso')
    total = models.DecimalField('total', max_digits=12, decimal_places=2)
    moneda = models.CharField('moneda', max_length=10, default='COP')
    metodo_pago = models.CharField('método de pago', max_length=12, choices=METODO_PAGO_CHOICES, default='whatsapp')
    pago_estado = models.CharField('estado del pago', max_length=10, choices=PAGO_ESTADO_CHOICES, default='pendiente')
    pago_referencia_externa = models.CharField(
        'referencia externa del pago', max_length=120, blank=True,
        help_text='ID de la preferencia/orden/pago en Mercado Pago o PayPal.',
    )
    referido_codigo = models.CharField('código de referido usado', max_length=40, blank=True)
    referido_recompensado = models.BooleanField('recompensa de referido ya acreditada', default=False)
    cupon_codigo = models.CharField('cupón usado', max_length=40, blank=True)
    cupon_contabilizado = models.BooleanField('uso del cupón ya contabilizado', default=False)
    credito_usado = models.DecimalField('crédito de la cuenta usado', max_digits=12, decimal_places=2, default=0)
    credito_descontado = models.BooleanField('crédito ya descontado de la cuenta', default=False)

    class Meta:
        verbose_name = 'pedido'
        verbose_name_plural = 'pedidos'
        ordering = ['-fecha']

    def __str__(self):
        return self.ref


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    juego = models.ForeignKey('catalog.Juego', on_delete=models.SET_NULL, null=True, related_name='items_vendidos')
    titulo = models.CharField('título', max_length=160, blank=True)
    precio_unitario = models.DecimalField('precio unitario', max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField('cantidad', default=1)
    cuenta = models.CharField('tipo de cuenta', max_length=12, blank=True, help_text='primaria / secundaria (vacío si no aplica).')
    credenciales_entregadas = models.TextField('credenciales entregadas', blank=True)

    def __str__(self):
        return self.titulo or (self.juego.title if self.juego else 'Ítem')

    def save(self, *args, **kwargs):
        if not self.titulo and self.juego:
            self.titulo = self.juego.title[:160]
        super().save(*args, **kwargs)


class MovimientoCredito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='movimientos')
    concepto = models.CharField('concepto', max_length=160)
    fecha = models.DateTimeField('fecha', auto_now_add=True)
    monto = models.DecimalField('monto', max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'movimiento de crédito'
        verbose_name_plural = 'movimientos de crédito'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.usuario} · {self.concepto} · {self.monto}'


class Reclamo(models.Model):
    ESTADO_CHOICES = [
        ('Abierto', 'Abierto'),
        ('Resuelto', 'Resuelto'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reclamos')
    ref = models.CharField('referencia', max_length=20, unique=True, default=_new_reclamo_ref)
    estado = models.CharField('estado', max_length=10, choices=ESTADO_CHOICES, default='Abierto')
    asunto = models.CharField('asunto', max_length=160)
    pedido = models.ForeignKey(Pedido, on_delete=models.SET_NULL, null=True, blank=True, related_name='reclamos')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'reclamo'
        verbose_name_plural = 'reclamos'
        ordering = ['-created_at']

    def __str__(self):
        return self.ref


class MensajeReclamo(models.Model):
    AUTOR_CHOICES = [
        ('cliente', 'Cliente'),
        ('admin', 'Administrador'),
    ]

    reclamo = models.ForeignKey(Reclamo, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.CharField('autor', max_length=10, choices=AUTOR_CHOICES)
    texto = models.TextField('mensaje')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f'{self.reclamo.ref} · {self.autor}'
