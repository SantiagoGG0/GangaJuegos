from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = 'apps.catalog'

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from . import snapshot
        from .models import Cover, Divisa, HeroVideo, Juego

        # Cualquier cambio en estos modelos invalida la caché del catálogo.
        for model in (Juego, Cover, HeroVideo, Divisa):
            post_save.connect(snapshot.bump, sender=model, dispatch_uid=f'catalog-bump-save-{model.__name__}')
            post_delete.connect(snapshot.bump, sender=model, dispatch_uid=f'catalog-bump-delete-{model.__name__}')
