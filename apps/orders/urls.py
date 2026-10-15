from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('agregar/', views.cart_add, name='cart_add'),
    path('quitar/<int:index>/', views.cart_remove, name='cart_remove'),
    path('cantidad/<int:index>/', views.cart_set_qty, name='cart_set_qty'),
    path('vaciar/', views.cart_clear, name='cart_clear'),
    path('referido/aplicar/', views.apply_referral, name='apply_referral'),
    path('referido/quitar/', views.remove_referral, name='remove_referral'),
    path('cupon/aplicar/', views.apply_coupon, name='apply_coupon'),
    path('cupon/quitar/', views.remove_coupon, name='remove_coupon'),
    path('credito/toggle/', views.toggle_credit, name='toggle_credit'),

    path('pagar/mercadopago/', views.checkout_mercadopago, name='checkout_mercadopago'),
    path('pagar/mercadopago/retorno/', views.mercadopago_return, name='mercadopago_return'),
    path('pagar/mercadopago/webhook/', views.mercadopago_webhook, name='mercadopago_webhook'),

    path('pagar/paypal/', views.checkout_paypal, name='checkout_paypal'),
    path('pagar/paypal/retorno/', views.paypal_return, name='paypal_return'),
    path('pagar/paypal/cancelar/', views.paypal_cancel, name='paypal_cancel'),
]
