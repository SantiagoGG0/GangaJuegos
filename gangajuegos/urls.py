from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from apps.panel.admin_site import gs_admin_site

urlpatterns = [
    path('admin/', gs_admin_site.urls),
    path('carrito/', include('apps.orders.urls')),
    path('', include('apps.store.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
