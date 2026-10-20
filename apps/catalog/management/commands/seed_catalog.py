import csv
import json
import re
import unicodedata
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.store.constants import REVIEWS_FALLBACK

from apps.catalog.models import (
    Combo,
    Cupon,
    Divisa,
    GiftCard,
    Juego,
    PlusPlan,
    SiteSettings,
    Testimonial,
    TierInfo,
)

DESIGN_DIR = None  # se resuelve en handle()

FEATURED_TITLES = ["God of War Ragnarök", "Spider-Man 2", "Ghost of Yōtei"]

RATES = {
    "USD": "3436", "USDEC": "3436", "MXN": "196", "ARS": "2.33",
    "PEN": "1008", "CLP": "3.73", "PYG": "0.4708",
}
VES_BCV_EUR = "947.3"

CURRENCY_LIST = [
    {"code": "COP", "flag": "🇨🇴", "name": "Colombia"},
    {"code": "USD", "flag": "🇺🇸", "name": "Estados Unidos"},
    {"code": "USDEC", "flag": "🇪🇨", "name": "Ecuador"},
    {"code": "MXN", "flag": "🇲🇽", "name": "México"},
    {"code": "ARS", "flag": "🇦🇷", "name": "Argentina"},
    {"code": "PEN", "flag": "🇵🇪", "name": "Perú"},
    {"code": "CLP", "flag": "🇨🇱", "name": "Chile"},
    {"code": "VES", "flag": "🇻🇪", "name": "Venezuela"},
    {"code": "PYG", "flag": "🇵🇾", "name": "Paraguay"},
]

PLUS_PLANS = [
    {"tier": "Essential", "months": 1, "price": 9900},
    {"tier": "Essential", "months": 3, "price": 21900},
    {"tier": "Essential", "months": 12, "price": 76000},
    {"tier": "Extra", "months": 1, "price": 11900},
    {"tier": "Extra", "months": 3, "price": 25900},
    {"tier": "Extra", "months": 12, "price": 69000},
    {"tier": "Deluxe", "months": 1, "price": 18000},
    {"tier": "Deluxe", "months": 3, "price": 41000},
    {"tier": "Deluxe", "months": 12, "price": 110000},
]

TIER_INFO = {
    "Essential": {"label": "Plan básico", "body": "Juego en línea, juegos mensuales y almacenamiento en la nube.", "recommended": False},
    "Extra": {"label": "Plan más popular", "body": "Todo lo de Essential más el catálogo de cientos de juegos.", "recommended": True},
    "Deluxe": {"label": "Plan completo", "body": "Todo lo de Extra más el catálogo clásico y pruebas de juegos.", "recommended": False},
}

COMBOS = [
    {"title": "Pack Aventura PS5", "games": ["God of War Ragnarök", "Spider-Man 2", "Horizon Forbidden West"], "sec": 219900, "pri": 319900},
    {"title": "Pack Terror", "games": ["Resident Evil 4 Remake", "Resident Evil Village", "Silent Hill 2"], "sec": 199900, "pri": 289900},
    {"title": "Pack Shooters", "games": ["Call of Duty: Black Ops 6", "Battlefield 6", "Helldivers 2"], "sec": 249900, "pri": 349900},
]

GIFTCARDS = [
    {"region": "PSN USA", "denomination": 2, "price": 12900},
    {"region": "PSN USA", "denomination": 5, "price": 27900},
    {"region": "PSN USA", "denomination": 10, "price": 45900},
    {"region": "PSN USA", "denomination": 20, "price": 89900},
    {"region": "PSN USA", "denomination": 25, "price": 109900},
    {"region": "PSN USA", "denomination": 50, "price": 214900},
    {"region": "PSN USA", "denomination": 100, "price": 419900},
]

# Las fechas "vence" del prototipo asumían un "hoy" de comienzos de 2026; el
# estado (Activo/Agotado) del panel se calcula en vivo contra la fecha real,
# así que se desplazan un año para conservar el mismo resultado visual
# (3 activos + NAVIDAD25 agotado por haber llegado a su tope de usos) sin
# quedar “vencidos” por el simple paso del tiempo.
FEATURED_TAGLINES = {
    "God of War Ragnarök": "La saga nórdica completa, en tu consola hoy.",
    "Spider-Man 2": "Nueva York otra vez, y esta vez con dos arañas.",
    "Ghost of Yōtei": "Hokkaido, venganza y una espada. Lo nuevo de PS5.",
}

TESTIMONIALS = [{"name": t["name"], "text": t["text"]} for t in REVIEWS_FALLBACK]

COUPONS = [
    {"code": "BIENVENIDO10", "tipo": "porcentaje", "valor": "10", "usos_actuales": 184, "usos_max": 500, "vence": date(2027, 12, 31)},
    {"code": "PSPLUS15", "tipo": "porcentaje", "valor": "15", "usos_actuales": 62, "usos_max": 200, "vence": date(2027, 4, 30)},
    {"code": "ECUADOR5", "tipo": "monto_fijo", "valor": "5", "usos_actuales": 41, "usos_max": 100, "vence": date(2027, 5, 15)},
    {"code": "NAVIDAD25", "tipo": "porcentaje", "valor": "25", "usos_actuales": 500, "usos_max": 500, "vence": date(2027, 1, 6)},
]

ADMIN_SEED = {"email": "admin@gangajuegos.com", "pass": "admin123", "nombre": "Administrador", "whatsapp": "+57 300 000 0000", "pais": "Colombia", "role": "admin", "credit": 0}

CLIENT_SEEDS = [
    {"email": "ana.gomez@gmail.com", "pass": "123456", "nombre": "Ana María Gómez", "whatsapp": "+57 311 482 9033", "pais": "Colombia", "role": "cliente", "credit": 12000},
    {"email": "kevin.andrade@outlook.com", "pass": "123456", "nombre": "Kevin Andrade", "whatsapp": "+593 98 774 1120", "pais": "Ecuador", "role": "cliente", "credit": 0},
    {"email": "sofia.nav@gmail.com", "pass": "123456", "nombre": "Sofía Navarro", "whatsapp": "+52 55 8841 2077", "pais": "México", "role": "cliente", "credit": 30000},
]


class Command(BaseCommand):
    help = "Siembra la base de datos con el catálogo y los datos exactos del prototipo Ganga Juegos."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Borra los datos existentes antes de sembrar.")

    def handle(self, *args, **options):
        global DESIGN_DIR
        from django.conf import settings
        DESIGN_DIR = settings.BASE_DIR / "seed_data"

        if options["reset"]:
            self.stdout.write("Borrando datos existentes...")
            Juego.objects.all().delete()
            Combo.objects.all().delete()
            PlusPlan.objects.all().delete()
            TierInfo.objects.all().delete()
            GiftCard.objects.all().delete()
            Cupon.objects.all().delete()
            Divisa.objects.all().delete()

        with transaction.atomic():
            self._seed_juegos()
            self._seed_usuarios()
            self._seed_combos()
            self._seed_plus_plans()
            self._seed_giftcards()
            self._seed_cupones()
            self._seed_divisas()
            self._seed_testimonials()
            self._seed_site_settings()

        self.stdout.write(self.style.SUCCESS("Catálogo sembrado correctamente."))

    # -- juegos -----------------------------------------------------------

    def _seed_juegos(self):
        games_js_path = DESIGN_DIR / "games.js"
        csv_path = DESIGN_DIR / "plantilla-catalogo-gamesstation.csv"

        txt = games_js_path.read_text(encoding="utf-8")
        start, end = txt.index("["), txt.rindex("]")
        games_full = json.loads(txt[start:end + 1])

        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            csv_rows = list(csv.DictReader(f, delimiter=";"))

        if len(games_full) != len(csv_rows):
            self.stdout.write(self.style.WARNING(
                f"games.js tiene {len(games_full)} juegos y el CSV tiene {len(csv_rows)}: revisa el desfase."
            ))

        created = 0
        for g, row in zip(games_full, csv_rows):
            if g["t"] != row["Título"]:
                self.stdout.write(self.style.WARNING(f'Desfase de orden: "{g["t"]}" vs "{row["Título"]}"'))

            juego, is_new = Juego.objects.update_or_create(
                slug=row["Slug"],
                defaults={
                    "title": g["t"],
                    "platform": g["p"],
                    "genre": g["gn"],
                    "price_secondary": g["sec"],
                    "price_primary": g["pri"],
                    "old_price_secondary": g.get("oSec"),
                    "old_price_primary": g.get("oPri"),
                    "active": row["Activo"].strip().lower() in ("sí", "si", "true", "1"),
                    "featured": row["Destacado"].strip().lower() in ("sí", "si", "true", "1") or g["t"] in FEATURED_TITLES,
                    "tagline": FEATURED_TAGLINES.get(g["t"], ""),
                    "notas": row["Notas"] or "",
                },
            )
            created += int(is_new)

        self.stdout.write(f"Juegos: {Juego.objects.count()} en BD ({created} nuevos).")

    # -- usuarios -----------------------------------------------------------

    def _seed_usuarios(self):
        Usuario = get_user_model()

        if not Usuario.objects.filter(email=ADMIN_SEED["email"]).exists():
            admin = Usuario.objects.create_superuser(
                email=ADMIN_SEED["email"],
                password=ADMIN_SEED["pass"],
                nombre=ADMIN_SEED["nombre"],
                whatsapp=ADMIN_SEED["whatsapp"],
                pais=ADMIN_SEED["pais"],
                role=ADMIN_SEED["role"],
                credit=ADMIN_SEED["credit"],
            )
            self.stdout.write(f"Usuario admin creado: {admin.email} / {ADMIN_SEED['pass']}")
        else:
            self.stdout.write("Usuario admin ya existe, se omite.")

        for seed in CLIENT_SEEDS:
            if Usuario.objects.filter(email=seed["email"]).exists():
                continue
            Usuario.objects.create_user(
                email=seed["email"],
                password=seed["pass"],
                nombre=seed["nombre"],
                whatsapp=seed["whatsapp"],
                pais=seed["pais"],
                role=seed["role"],
                credit=seed["credit"],
            )
        self.stdout.write(f"Usuarios cliente: {Usuario.objects.filter(role='cliente').count()} en BD.")

    # -- combos / plus / giftcards / cupones / divisas ---------------------

    def _seed_combos(self):
        for c in COMBOS:
            combo, _ = Combo.objects.update_or_create(
                slug=slugify(c["title"]),
                defaults={"title": c["title"], "price_secondary": c["sec"], "price_primary": c["pri"]},
            )
            juegos = Juego.objects.filter(title__in=c["games"])
            combo.games.set(juegos)
        self.stdout.write(f"Combos: {Combo.objects.count()} en BD.")

    def _seed_plus_plans(self):
        for p in PLUS_PLANS:
            PlusPlan.objects.update_or_create(tier=p["tier"], months=p["months"], defaults={"price": p["price"]})
        for tier, info in TIER_INFO.items():
            TierInfo.objects.update_or_create(tier=tier, defaults=info)
        self.stdout.write(f"Planes PS Plus: {PlusPlan.objects.count()} en BD.")

    def _seed_giftcards(self):
        for gc in GIFTCARDS:
            GiftCard.objects.update_or_create(
                region=gc["region"], denomination=gc["denomination"], defaults={"price": gc["price"]}
            )
        self.stdout.write(f"Gift cards: {GiftCard.objects.count()} en BD.")

    def _seed_cupones(self):
        for c in COUPONS:
            Cupon.objects.update_or_create(
                code=c["code"],
                defaults={
                    "tipo": c["tipo"], "valor": c["valor"],
                    "usos_actuales": c["usos_actuales"], "usos_max": c["usos_max"], "vence": c["vence"],
                },
            )
        self.stdout.write(f"Cupones: {Cupon.objects.count()} en BD.")

    def _seed_testimonials(self):
        for i, t in enumerate(TESTIMONIALS):
            Testimonial.objects.update_or_create(name=t["name"], defaults={"text": t["text"], "order": i})
        self.stdout.write(f"Reseñas: {Testimonial.objects.count()} en BD.")

    def _seed_site_settings(self):
        SiteSettings.load()
        self.stdout.write("Configuración del sitio: lista.")

    def _seed_divisas(self):
        for c in CURRENCY_LIST:
            code = c["code"]
            if code == "COP":
                tasa = "1"
            elif code == "VES":
                tasa = VES_BCV_EUR
            else:
                tasa = RATES[code]
            Divisa.objects.update_or_create(
                codigo=code, defaults={"tasa": tasa, "pais": c["name"], "bandera": c["flag"]}
            )
        self.stdout.write(f"Divisas: {Divisa.objects.count()} en BD.")
