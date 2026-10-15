from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', 'cliente')
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True')
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('cliente', 'Cliente'),
    ]

    username = None
    email = models.EmailField('correo', unique=True)
    nombre = models.CharField('nombre', max_length=120)
    whatsapp = models.CharField('whatsapp', max_length=30, blank=True)
    pais = models.CharField('país', max_length=60, blank=True)
    role = models.CharField('rol', max_length=10, choices=ROLE_CHOICES, default='cliente')
    credit = models.DecimalField('crédito', max_digits=12, decimal_places=2, default=0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def is_admin_role(self):
        return self.role == 'admin'

    @property
    def since(self):
        return self.date_joined.date()


class Wishlist(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='deseos')
    juego = models.ForeignKey('catalog.Juego', on_delete=models.CASCADE, related_name='en_deseos')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'juego')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.usuario} → {self.juego}'


def _referral_code_for(nombre):
    import re
    import uuid
    base = re.sub(r'[^A-Z0-9]', '', (nombre or 'GAMER').split()[0].upper())[:10] or 'GAMER'
    for _ in range(20):
        code = f'GJ-{base}-{uuid.uuid4().hex[:4].upper()}'
        if not Referido.objects.filter(codigo=code).exists():
            return code
    return f'GJ-{base}-{uuid.uuid4().hex[:8].upper()}'


class Referido(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='referido')
    codigo = models.CharField('código', max_length=40, unique=True)
    invitados = models.PositiveIntegerField(default=0)
    con_compra = models.PositiveIntegerField(default=0)
    credito_ganado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.codigo

    @classmethod
    def get_or_create_for(cls, usuario):
        return cls.objects.get_or_create(usuario=usuario, defaults={'codigo': _referral_code_for(usuario.nombre)})
