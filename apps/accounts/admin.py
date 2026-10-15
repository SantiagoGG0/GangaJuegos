from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.panel.admin_site import gs_admin_site

from .models import Referido, Usuario, Wishlist


@admin.register(Usuario, site=gs_admin_site)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ['-date_joined']
    list_display = ['email', 'nombre', 'whatsapp', 'pais', 'role', 'credit', 'date_joined', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_active']
    search_fields = ['email', 'nombre', 'whatsapp']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Datos personales', {'fields': ('nombre', 'whatsapp', 'pais', 'role', 'credit')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'whatsapp', 'pais', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(Wishlist, site=gs_admin_site)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'juego', 'created_at']
    search_fields = ['usuario__email', 'juego__title']


@admin.register(Referido, site=gs_admin_site)
class ReferidoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'codigo', 'invitados', 'con_compra', 'credito_ganado']
    search_fields = ['usuario__email', 'codigo']
