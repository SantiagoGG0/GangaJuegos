from django.contrib import admin

from apps.panel.admin_site import gs_admin_site

from .models import ItemPedido, MensajeReclamo, MovimientoCredito, Pedido, Reclamo


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


@admin.register(Pedido, site=gs_admin_site)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['ref', 'usuario', 'fecha', 'estado', 'metodo_pago', 'pago_estado', 'total']
    list_filter = ['estado', 'metodo_pago', 'pago_estado']
    search_fields = ['ref', 'usuario__email', 'pago_referencia_externa']
    inlines = [ItemPedidoInline]


@admin.register(MovimientoCredito, site=gs_admin_site)
class MovimientoCreditoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'concepto', 'fecha', 'monto']
    search_fields = ['usuario__email', 'concepto']


class MensajeReclamoInline(admin.TabularInline):
    model = MensajeReclamo
    extra = 0


@admin.register(Reclamo, site=gs_admin_site)
class ReclamoAdmin(admin.ModelAdmin):
    list_display = ['ref', 'usuario', 'asunto', 'estado', 'created_at']
    list_filter = ['estado']
    search_fields = ['ref', 'usuario__email', 'asunto']
    inlines = [MensajeReclamoInline]
