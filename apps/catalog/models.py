import datetime
import os
import uuid

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


PLATFORM_CHOICES = [
    ('PS4', 'PS4'),
    ('PS5', 'PS5'),
    ('PS4/PS5', 'PS4/PS5'),
]


class Juego(models.Model):
    title = models.CharField('título', max_length=255)
    slug = models.SlugField('slug', max_length=180, unique=True)
    platform = models.CharField('plataforma', max_length=10, choices=PLATFORM_CHOICES)
    genre = models.CharField('género', max_length=120)
    price_secondary = models.PositiveIntegerField('precio secundaria')
    price_primary = models.PositiveIntegerField('precio primaria')
    old_price_secondary = models.PositiveIntegerField('precio antes secundaria', null=True, blank=True)
    old_price_primary = models.PositiveIntegerField('precio antes primaria', null=True, blank=True)
    active = models.BooleanField('activo', default=True)
    featured = models.BooleanField('destacado', default=False)
    tagline = models.CharField(
        'frase destacada', max_length=160, blank=True,
        help_text='Solo se usa si el juego está marcado como destacado (aparece en el carrusel del home).',
    )
    notas = models.TextField('notas', blank=True)
    oferta_termina = models.DateField(
        'la oferta termina', null=True, blank=True,
        help_text='Opcional. Al pasar esta fecha la oferta se retira sola y el juego vuelve a su precio anterior.',
    )

    class Meta:
        verbose_name = 'juego'
        verbose_name_plural = 'juegos'
        ordering = ['title']

    def __str__(self):
        return self.title

    @property
    def has_discount(self):
        return bool(self.old_price_secondary or self.old_price_primary)

    @property
    def discount_percent(self):
        if self.old_price_primary and self.old_price_primary > self.price_primary:
            return round((1 - self.price_primary / self.old_price_primary) * 100)
        if self.old_price_secondary and self.old_price_secondary > self.price_secondary:
            return round((1 - self.price_secondary / self.old_price_secondary) * 100)
        return 0

    @property
    def initials(self):
        words = [w for w in self.title.split(' ') if w]
        return ''.join(w[0].upper() for w in words[:2]) or '??'


def cover_upload_to(instance, filename):
    # Nombre único por versión: nginx sirve /media/ con caché larga en el
    # navegador, así que una carátula nueva debe tener una URL nueva.
    ext = os.path.splitext(filename)[1].lower() or '.jpg'
    return f'covers/{instance.juego.slug}-{uuid.uuid4().hex[:8]}{ext}'


class Cover(models.Model):
    juego = models.OneToOneField(Juego, on_delete=models.CASCADE, related_name='cover')
    image = models.ImageField('imagen', upload_to=cover_upload_to)
    uploaded_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Carátula de {self.juego.title}'


class Combo(models.Model):
    title = models.CharField('título', max_length=160)
    slug = models.SlugField('slug', max_length=180, unique=True)
    games = models.ManyToManyField(Juego, related_name='combos', verbose_name='juegos')
    price_secondary = models.PositiveIntegerField('precio secundaria')
    price_primary = models.PositiveIntegerField('precio primaria')

    class Meta:
        verbose_name = 'combo'
        verbose_name_plural = 'combos'

    def __str__(self):
        return self.title


TIER_CHOICES = [
    ('Essential', 'Essential'),
    ('Extra', 'Extra'),
    ('Deluxe', 'Deluxe'),
]

MONTHS_CHOICES = [
    (1, '1 mes'),
    (3, '3 meses'),
    (12, '12 meses'),
]


class PlusPlan(models.Model):
    PLATFORM_CHOICES = [('PS5', 'PS5'), ('PS4', 'PS4')]

    tier = models.CharField('tier', max_length=12, choices=TIER_CHOICES)
    platform = models.CharField('plataforma', max_length=3, choices=PLATFORM_CHOICES, default='PS5')
    months = models.PositiveSmallIntegerField('meses', choices=MONTHS_CHOICES)
    price = models.PositiveIntegerField('precio')

    class Meta:
        verbose_name = 'plan PS Plus'
        verbose_name_plural = 'planes PS Plus'
        unique_together = ('tier', 'platform', 'months')
        ordering = ['platform', 'tier', 'months']

    def __str__(self):
        return f'{self.tier} {self.platform} · {self.months} mes(es)'


class TierInfo(models.Model):
    tier = models.CharField('tier', max_length=12, choices=TIER_CHOICES, unique=True)
    label = models.CharField('etiqueta', max_length=80)
    body = models.TextField('descripción')
    recommended = models.BooleanField('recomendado', default=False)

    class Meta:
        verbose_name = 'info de tier'
        verbose_name_plural = 'info de tiers'

    def __str__(self):
        return self.tier


class GiftCard(models.Model):
    region = models.CharField('región', max_length=60)
    denomination = models.PositiveIntegerField('denominación (USD)')
    price = models.PositiveIntegerField('precio (COP)')

    class Meta:
        verbose_name = 'gift card'
        verbose_name_plural = 'gift cards'
        unique_together = ('region', 'denomination')
        ordering = ['denomination']

    def __str__(self):
        return f'{self.region} · USD {self.denomination}'


class Cupon(models.Model):
    TIPO_CHOICES = [
        ('porcentaje', 'Porcentaje'),
        ('monto_fijo', 'Monto fijo'),
    ]

    code = models.CharField('código', max_length=40, unique=True)
    tipo = models.CharField('tipo', max_length=12, choices=TIPO_CHOICES)
    valor = models.DecimalField('valor', max_digits=10, decimal_places=2)
    usos_actuales = models.PositiveIntegerField('usos actuales', default=0)
    usos_max = models.PositiveIntegerField('usos máximos', null=True, blank=True, help_text='Vacío = sin límite.')
    vence = models.DateField('vence', null=True, blank=True, help_text='Vacío = sin vencimiento.')
    activo = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'cupón'
        verbose_name_plural = 'cupones'
        ordering = ['-id']

    def __str__(self):
        return self.code

    @property
    def estado(self):
        if not self.activo:
            return 'Oculto'
        if (self.usos_max and self.usos_actuales >= self.usos_max) or (self.vence and self.vence < timezone.localdate()):
            return 'Agotado'
        return 'Activo'

    @property
    def valor_display(self):
        """Porcentaje ('10%') o monto fijo en COP ('$ 20.000') — la base de
        precios de toda la tienda es COP."""
        if self.tipo == 'porcentaje':
            return f'{self.valor.normalize():f}'.rstrip('.') + '%'
        from .pricing import money
        return money(self.valor, 'COP', allow_free=False)

    @property
    def uso_display(self):
        if self.usos_max:
            return f'{self.usos_actuales} de {self.usos_max}'
        return f'{self.usos_actuales} · sin límite'


class SaldoCodigo(models.Model):
    """Código canjeable por crédito de cuenta (COP) — se canjea desde el
    perfil del usuario ('Saldo'), no en el carrito. `usos_max` limita cuántas
    veces se puede canjear EN TOTAL (entre todos los usuarios), configurable
    desde el admin."""
    codigo = models.CharField('código', max_length=40, unique=True)
    monto = models.PositiveIntegerField('monto a acreditar (COP)')
    usos_max = models.PositiveIntegerField('usos máximos (total, entre todos los usuarios)', default=1)
    usos_actuales = models.PositiveIntegerField('usos actuales', default=0)
    activo = models.BooleanField('activo', default=True)
    creado = models.DateTimeField('creado', auto_now_add=True)

    class Meta:
        verbose_name = 'código de saldo'
        verbose_name_plural = 'códigos de saldo'
        ordering = ['-creado']

    def __str__(self):
        return self.codigo

    @property
    def estado(self):
        if not self.activo or self.usos_actuales >= self.usos_max:
            return 'Agotado'
        return 'Activo'

    @property
    def uso_display(self):
        return f'{self.usos_actuales} / {self.usos_max}'


class Divisa(models.Model):
    codigo = models.CharField('código ISO', max_length=10, unique=True)
    tasa = models.DecimalField('tasa', max_digits=12, decimal_places=4)
    actualizado = models.DateTimeField('actualizado', auto_now=True)
    pais = models.CharField('país', max_length=60)
    bandera = models.CharField('bandera', max_length=10)

    class Meta:
        verbose_name = 'divisa'
        verbose_name_plural = 'divisas'
        ordering = ['codigo']

    def __str__(self):
        return self.codigo


class Testimonial(models.Model):
    name = models.CharField('nombre / usuario', max_length=80)
    text = models.TextField('reseña')
    order = models.PositiveIntegerField('orden', default=0)
    active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'reseña'
        verbose_name_plural = 'reseñas (home)'
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'm4v', 'ogg', 'ogv']


def hero_video_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or '.mp4'
    return f'site/hero-videos/{instance.juego.slug}{ext}'


class HeroVideo(models.Model):
    """Carrusel de video del hero de inicio. Cada video está ligado a un
    juego destacado: al cambiar de video cambia también la tarjeta flotante
    de precio/CTA que se muestra sobre él."""
    juego = models.OneToOneField(Juego, on_delete=models.CASCADE, related_name='hero_video')
    video = models.FileField(
        'video', upload_to=hero_video_upload_to,
        validators=[FileExtensionValidator(allowed_extensions=VIDEO_EXTENSIONS)],
        help_text='Formatos permitidos: ' + ', '.join(VIDEO_EXTENSIONS) + '. Se reproduce en silencio y en bucle, recortado a la forma del contenedor.',
    )
    poster = models.ImageField(
        'imagen de vista previa', upload_to='site/hero-videos/posters/', blank=True, null=True,
        help_text='Se muestra mientras el video carga o si el navegador no puede reproducirlo. Si no subes una, se usa la carátula del juego.',
    )
    order = models.PositiveIntegerField('orden', default=0)
    active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'video del hero'
        verbose_name_plural = 'videos del hero (home)'
        ordering = ['order', 'id']

    def __str__(self):
        return f'Video de {self.juego.title}'


class SiteSettings(models.Model):
    """Fila única con contenido editable del home que en el prototipo estaba
    hardcodeado (cifra de reseñas, miniatura/video de comentarios).

    Esta tabla vive en la misma base de datos que Gamesstation (catálogo y
    pedidos compartidos), pero cada marca debe poder configurar su propio
    WhatsApp/correo/switches de pago sin pisar al otro sitio — por eso la fila
    no usa siempre pk=1: cada codebase define su propio SITE_SETTINGS_PK."""
    SITE_SETTINGS_PK = 2
    review_count = models.PositiveIntegerField('cantidad de reseñas', default=312)
    review_video_file = models.FileField(
        'video de comentarios', upload_to='site/videos/', blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=VIDEO_EXTENSIONS)],
        help_text='Formatos permitidos: ' + ', '.join(VIDEO_EXTENSIONS) + '. Se reproduce en silencio y en bucle.',
    )
    review_video_image = models.ImageField(
        'miniatura de respaldo (si no hay video)', upload_to='site/', blank=True, null=True,
        help_text='Se usa como imagen fija si no subes un video, o como carátula mientras el video carga.',
    )
    review_video_url = models.URLField('enlace al post de Instagram', blank=True)
    review_video_caption = models.CharField(
        'texto sobre la miniatura (si no hay video ni imagen)', max_length=160, blank=True,
        default='video de la publicación con los comentarios',
    )
    instagram_handle = models.CharField('usuario de Instagram', max_length=60, blank=True, default='@gangajuegos')
    instagram_followers_label = models.CharField(
        'texto de seguidores', max_length=40, blank=True, default='Síguenos',
        help_text='Ej: "35K seguidores". Déjalo como "Síguenos" mientras no tengas una cifra real que mostrar.',
    )
    instagram_active = models.BooleanField('mostrar como "activos" (punto verde)', default=True)
    instagram_url = models.URLField('enlace al perfil de Instagram', blank=True)

    whatsapp_number = models.CharField(
        'número de WhatsApp principal (ventas)', max_length=20, blank=True,
        help_text='Solo dígitos con código de país, ej: 573000000000. Se usa para pedidos, carrito y asesoría, '
                  'y en el botón flotante y soporte si esos no tienen un número propio.',
    )
    whatsapp_button_number = models.CharField(
        'número del botón flotante de WhatsApp', max_length=20, blank=True,
        help_text='Opcional. Vacío = usa el número principal.',
    )
    whatsapp_support_number = models.CharField(
        'número de WhatsApp de soporte', max_length=20, blank=True,
        help_text='Opcional. Ayuda, problemas para ingresar, estado de pedidos y garantía. Vacío = usa el número principal.',
    )
    whatsapp_community_url = models.URLField(
        'enlace de la comunidad/canal de WhatsApp', blank=True,
        help_text='Enlace real de invitación al canal o comunidad de WhatsApp (ej. https://whatsapp.com/channel/...). Se usa en el botón "Unirme al canal" del home.',
    )
    promo_coupon = models.CharField(
        'cupón promocionado', max_length=40, blank=True,
        help_text='Código de un cupón activo que se anuncia en la cinta superior y en la píldora flotante del home/catálogo. Vacío = no se anuncia ninguno.',
    )
    review_rating = models.DecimalField('calificación promedio', max_digits=2, decimal_places=1, default=4.9)
    support_email = models.EmailField(
        'correo de soporte', blank=True,
        help_text='Se muestra en el footer, ayuda, términos y privacidad. Si se deja vacío, esas secciones no muestran correo (solo WhatsApp).',
    )

    referral_enabled = models.BooleanField('permitir código de referido en el carrito', default=True)
    referral_reward_pct = models.PositiveIntegerField(
        'crédito para el dueño del código (% de la compra referida)', default=10,
        help_text='No descuenta la compra inicial del referido — se acredita al dueño del código, para usar en una compra futura, cuando el pedido referido queda aprobado.',
    )

    mercadopago_enabled = models.BooleanField(
        'habilitar pago con Mercado Pago', default=False,
        help_text='Si está desactivado, el botón de Mercado Pago no aparece en el carrito.',
    )
    paypal_enabled = models.BooleanField(
        'habilitar pago con PayPal', default=False,
        help_text='Si está desactivado, el botón de PayPal no aparece en el carrito.',
    )

    class Meta:
        verbose_name = 'configuración del sitio'
        verbose_name_plural = 'configuración del sitio'

    def __str__(self):
        return 'Configuración del sitio'

    def save(self, *args, **kwargs):
        self.pk = self.SITE_SETTINGS_PK
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        """Configuración para LEER (cacheada: no modificar ni guardar esta
        instancia). Para editar usar `load_fresh()`."""
        from . import snapshot
        return snapshot.cached('site_settings', cls.load_fresh)

    @classmethod
    def load_fresh(cls):
        obj, _ = cls.objects.get_or_create(pk=cls.SITE_SETTINGS_PK)
        return obj


class SiteEvent(models.Model):
    """Registro mínimo de actividad real del sitio (sin datos personales),
    usado para que el panel de administración muestre visitas/conversión/
    funnel con cifras reales en vez de los valores fijos del prototipo."""
    KIND_CHOICES = [
        ('visita', 'Visita de página'),
        ('ficha', 'Vista de ficha de producto'),
        ('carrito', 'Agregado al carrito'),
        ('compra', 'Compra confirmada'),
    ]
    kind = models.CharField('tipo', max_length=10, choices=KIND_CHOICES)
    created_at = models.DateTimeField('fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'evento de sitio'
        verbose_name_plural = 'eventos de sitio'
        indexes = [models.Index(fields=['kind', 'created_at'])]

    def __str__(self):
        return f'{self.kind} · {self.created_at:%Y-%m-%d %H:%M}'
