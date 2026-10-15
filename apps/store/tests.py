import json
import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalog import snapshot
from apps.catalog.models import Juego
from apps.store import views

PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(STORAGES=PLAIN_STORAGES, SECURE_SSL_REDIRECT=False)
class CatalogPerformanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Juego.objects.bulk_create([
            Juego(title=f'Juego {i:03d}', slug=f'juego-{i:03d}', platform='PS5' if i % 2 else 'PS4',
                  genre='Acción/Aventura' if i % 3 else 'Deportes', price_primary=100000 + i, price_secondary=50000 + i,
                  old_price_primary=200000 if i % 5 == 0 else None)
            for i in range(120)
        ])

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.stamp = override_settings(CATALOG_STAMP_FILE=f'{self.tmp}/stamp')
        self.stamp.enable()
        snapshot.bump()

    def tearDown(self):
        self.stamp.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_catalog_renders_first_batch_only(self):
        resp = self.client.get(reverse('store:catalog'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['games']), views.CATALOG_PAGE)
        self.assertEqual(resp.context['result_count'], 120)
        self.assertIn('page=2', resp.context['more_url'])
        self.assertContains(resp, 'data-card="1"', count=views.CATALOG_PAGE)

    def test_page_param_without_js(self):
        resp = self.client.get(reverse('store:catalog'), {'page': 3})
        self.assertEqual(len(resp.context['games']), 120)
        self.assertEqual(resp.context['more_url'], '')

    def test_filters_and_sort_on_server(self):
        resp = self.client.get(reverse('store:catalog'), {'platform': 'PS5', 'sort': 'Menor precio'})
        games = resp.context['games']
        self.assertEqual(resp.context['result_count'], 60)
        self.assertTrue(all('PS5' in g['plat'] for g in games))
        self.assertEqual([g['sec_cop'] for g in games], sorted(g['sec_cop'] for g in games))
        deals = self.client.get(reverse('store:deals'))
        self.assertEqual(deals.context['result_count'], 24)

    def test_catalog_data_json(self):
        resp = self.client.get(reverse('store:catalog_data'), {'cur': 'COP', 'v': '1'})
        self.assertEqual(resp['Content-Type'], 'application/json')
        self.assertIn('max-age', resp['Cache-Control'])
        rows = json.loads(resp.content)
        self.assertEqual(len(rows), 120)
        self.assertEqual(set(rows[0]) >= {'u', 't', 'p', 'g', 'a', 'b', 's', 'dp'}, True)

    def test_cache_is_invalidated_when_a_game_changes(self):
        self.client.get(reverse('store:catalog'))
        j = Juego.objects.get(slug='juego-001')
        j.title = 'Juego renombrado'
        j.save()
        rows = json.loads(self.client.get(reverse('store:catalog_data')).content)
        self.assertIn('Juego renombrado', [r['t'] for r in rows])
        Juego.objects.filter(slug='juego-002').update(active=False)  # .update() no dispara señales
        snapshot.bump()
        self.assertEqual(self.client.get(reverse('store:catalog')).context['result_count'], 119)

    def test_home_offer_rail_is_limited(self):
        resp = self.client.get(reverse('store:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.context['deals']), views.HOME_RAIL)

    def test_search_api_uses_cache(self):
        self.client.get(reverse('store:search_api'), {'q': 'juego'})
        with self.assertNumQueries(0):
            data = self.client.get(reverse('store:search_api'), {'q': 'juego 01'}).json()
        self.assertEqual(data['total'], 10)
