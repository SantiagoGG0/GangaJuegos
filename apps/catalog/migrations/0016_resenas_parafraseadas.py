"""Reescribe con otras palabras las 6 reseñas iniciales del home (mismo
contenido, sin agregar ni cambiar lo que dice cada cliente). Solo toca una
reseña si todavía tiene su texto original: si alguien ya la editó desde el
admin, se respeta."""
from django.db import migrations

# usuario -> (textos originales posibles, texto nuevo)
REWRITES = {
    'diego.cst.11': (
        ['Vuelvo a dejar otro comentario por aquí, es la segunda vez que compro un juego con ellos, la verdad no sé cómo le hacen para tener los precios tan bajos pero en realidad se agradece, gracias chicos, todo bien como siempre.',
         'Vuelvo a dejar otro comentario por aquí, es la segunda vez que compro un juego con ellos, la verdad no sé cómo le hacen para tener los precios tan bajos pero en realidad se agradece.'],
        'Paso de nuevo a comentar: ya es la segunda vez que les compro un juego. Sigo sin entender cómo consiguen precios tan bajos, pero se agradece mucho. Gracias, todo bien otra vez.',
    ),
    'carmelo_j96': (
        ['Compré Dragon Ball Z Kakarot por recomendación de un amigo, me funciona 10/10, atención al cliente excelente, recomendado 100%.'],
        'Un amigo me los recomendó y compré Dragon Ball Z Kakarot. Funciona perfecto y la atención fue excelente; los recomiendo sin dudarlo.',
    ),
    'melissa_alvarez_2': (
        ['100% confiable, mi novio compró un juego y tardó más en pagarlo que en tenerlo en la consola. No busquen más, es la mejor opción para comprar los mejores juegos para la play.',
         '100% confiable, mi novio compró un juego y tardó más en pagarlo que en tenerlo en la consola.'],
        'Totalmente confiables: mi novio compró un juego y lo tuvo en la consola en menos tiempo del que le tomó pagarlo. Si buscan dónde comprar juegos para la Play, esta es la mejor opción.',
    ),
    'davismendoza78': (
        ['Muy confiables, compré 3 Call of Duty a un muy buen precio, super recomendado.'],
        'Les compré tres Call of Duty a muy buen precio. Son muy confiables, los recomiendo mucho.',
    ),
    'luisalejandroriverachavez': (
        ['Yo acabo de comprar The Last of Us Parte 2 sin ningún problema, súper eficientes y eficaces.'],
        'Acabo de comprar The Last of Us Parte II y todo salió sin ningún problema. Muy rápidos y eficientes.',
    ),
    'yeixon.blanco': (
        ['100% confiable y recomendable, acabo de comprar el FC 26 y ya lo estoy descargando.'],
        'Confiables y muy recomendados: compré el FC 26 y ya lo tengo descargando.',
    ),
}


def forwards(apps, schema_editor):
    Testimonial = apps.get_model('catalog', 'Testimonial')
    for name, (olds, new) in REWRITES.items():
        Testimonial.objects.filter(name=name, text__in=olds).update(text=new)


def backwards(apps, schema_editor):
    Testimonial = apps.get_model('catalog', 'Testimonial')
    for name, (olds, new) in REWRITES.items():
        Testimonial.objects.filter(name=name, text=new).update(text=olds[0])


class Migration(migrations.Migration):
    dependencies = [('catalog', '0015_whatsapp_numeros')]
    operations = [migrations.RunPython(forwards, backwards)]
