from django.contrib import admin
from django.urls import path


class GangaJuegosAdminSite(admin.AdminSite):
    site_header = 'Ganga Juegos · Panel'
    site_title = 'Ganga Juegos Panel'
    index_title = 'Administración avanzada'
    login_template = 'admin/login.html'

    def get_urls(self):
        from . import covers_views, dashboard_views as dv, products_bulk as pb

        custom = [
            path('', self.admin_view(dv.tab_resumen), name='dashboard_resumen'),
            path('avanzado/', self.admin_view(self.models_index), name='models_index'),
            path('pedidos/<int:pk>/entregar/', self.admin_view(dv.deliver_order), name='dashboard_deliver'),
            path('clientes/export.csv', self.admin_view(dv.export_clientes_csv), name='dashboard_export_clientes'),
            path('catalogo/', self.admin_view(dv.tab_catalogo), name='dashboard_catalogo'),
            path('catalogo/<int:pk>/toggle/', self.admin_view(dv.toggle_juego_active), name='dashboard_toggle_juego'),
            path('catalogo/<int:pk>/eliminar/', self.admin_view(dv.juego_delete), name='dashboard_juego_delete'),
            path('catalogo/acciones/', self.admin_view(dv.catalog_bulk), name='dashboard_catalog_bulk'),
            path('catalogo/eliminar-todo/', self.admin_view(dv.catalog_delete_all), name='dashboard_catalog_delete_all'),
            path('ofertas/', self.admin_view(dv.tab_ofertas), name='dashboard_ofertas'),
            path('ofertas/nueva/', self.admin_view(dv.offer_create), name='dashboard_offer_create'),
            path('ofertas/<int:pk>/quitar/', self.admin_view(dv.offer_remove), name='dashboard_offer_remove'),
            path('cupones/', self.admin_view(dv.tab_cupones), name='dashboard_cupones'),
            path('cupones/nuevo/', self.admin_view(dv.coupon_create), name='dashboard_coupon_create'),
            path('cupones/<int:pk>/toggle/', self.admin_view(dv.coupon_toggle), name='dashboard_coupon_toggle'),
            path('metricas/', self.admin_view(dv.tab_metricas), name='dashboard_metricas'),
            path('divisas/', self.admin_view(dv.tab_divisas), name='dashboard_divisas'),
            path('divisas/guardar/', self.admin_view(dv.save_rates), name='dashboard_save_rates'),
            path('caratulas/', self.admin_view(dv.tab_caratulas), name='covers_manager'),
            path('caratulas/upload/', self.admin_view(covers_views.covers_upload_ajax), name='covers_upload'),
            path('caratulas/asignar/<slug:slug>/', self.admin_view(covers_views.covers_assign_one), name='covers_assign_one'),
            path('caratulas/quitar/<slug:slug>/', self.admin_view(covers_views.covers_remove), name='covers_remove'),
            path('caratulas/export.csv', self.admin_view(covers_views.covers_export_csv), name='covers_export'),
            path('productos/carga-masiva/', self.admin_view(pb.products_bulk_view), name='products_bulk'),
            path('productos/carga-masiva/plantilla.csv', self.admin_view(pb.products_bulk_template), name='products_bulk_template'),
            path('productos/carga-masiva/subir/', self.admin_view(pb.products_bulk_upload), name='products_bulk_upload'),
            path('productos/carga-masiva/importar/', self.admin_view(pb.products_bulk_import), name='products_bulk_import'),
            path('productos/carga-masiva/reiniciar/', self.admin_view(pb.products_bulk_reset), name='products_bulk_reset'),
        ]
        return custom + super().get_urls()

    def models_index(self, request, extra_context=None):
        """Índice nativo de Django (todos los modelos: pedidos, usuarios,
        configuración del sitio, combos, planes PS Plus...)."""
        return admin.AdminSite.index(self, request, extra_context)

    def index(self, request, extra_context=None):
        from . import dashboard_views as dv
        return dv.tab_resumen(request)


gs_admin_site = GangaJuegosAdminSite(name='gsadmin')
