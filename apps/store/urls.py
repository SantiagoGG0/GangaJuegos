from django.urls import path

from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalogo/', views.catalog, name='catalog'),
    path('juego/<slug:slug>/', views.detail, name='detail'),
    path('carrito/', views.cart, name='cart'),
    path('ofertas/', views.deals, name='deals'),
    path('combos/', views.combos, name='combos'),
    path('plus/', views.plus, name='plus'),
    path('tarjetas-regalo/', views.giftcards, name='giftcards'),
    path('ayuda/', views.help_view, name='help'),
    path('terminos/', views.terms_view, name='terms'),
    path('privacidad/', views.privacy_view, name='privacy'),
    path('cuenta/entrar/', views.auth_view, name='auth'),
    path('cuenta/salir/', views.logout_view, name='logout'),
    path('cuenta/', views.account, name='account'),
    path('cuenta/saldo/canjear/', views.redeem_saldo_codigo, name='redeem_saldo_codigo'),
    path('deseos/<int:pk>/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    path('moneda/', views.set_currency, name='set_currency'),
    path('modo-precio/', views.set_price_mode, name='set_price_mode'),
    path('buscar/', views.search_api, name='search_api'),
]
