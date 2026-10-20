"""Contenido fijo del rediseño (copys, listas, textos legales) que no vive en
la base de datos. Se reproduce tal cual el diseño "Ganga Juegos Rediseño v4"."""

# géneros que se ofrecen como filtro (coincidencia por substring sobre el
# campo `genre` del juego, que puede ser compuesto: "Acción/Aventura").
GENRES = ['Acción', 'Aventura', 'Mundo abierto', 'RPG', 'Deportes', 'Carreras', 'Lucha', 'Shooter', 'Terror', 'Cooperativo', 'Plataformas']
GENRE_COLORS = ['#FC3C00', '#FC5F01', '#FC8B01', '#FCC602']

SORTS = ['Relevancia', 'Menor precio', 'Mayor descuento']

# bandera (dibujada con CSS, igual en cualquier sistema) e indicativo
# telefónico por código de Divisa.
FLAGS = {
    'COP': 'linear-gradient(180deg,#FCD116 0 50%,#003893 50% 75%,#CE1126 75%)',
    'VES': 'linear-gradient(180deg,#FCE300 0 33.4%,#00247D 33.4% 66.7%,#CF142B 66.7%)',
    'USDEC': 'linear-gradient(180deg,#FFDD00 0 50%,#034EA2 50% 75%,#ED1C24 75%)',
    'ARS': 'linear-gradient(180deg,#74ACDF 0 33.4%,#fff 33.4% 66.7%,#74ACDF 66.7%)',
    'PEN': 'linear-gradient(90deg,#D91023 0 33.4%,#fff 33.4% 66.7%,#D91023 66.7%)',
    'MXN': 'linear-gradient(90deg,#006847 0 33.4%,#fff 33.4% 66.7%,#CE1126 66.7%)',
    'CLP': 'linear-gradient(90deg,#0039A6 0 38%,transparent 38%) 0 0/100% 50% no-repeat,linear-gradient(180deg,#fff 0 50%,#D52B1E 50%)',
    'PYG': 'linear-gradient(180deg,#D52B1E 0 33.4%,#fff 33.4% 66.7%,#0038A8 66.7%)',
    'USD': 'linear-gradient(90deg,#3C3B6E 0 40%,transparent 40%) 0 0/100% 54% no-repeat,repeating-linear-gradient(180deg,#B22234 0 15.4%,#fff 15.4% 30.8%)',
}
DIALS = {'COP': '+57', 'VES': '+58', 'USDEC': '+593', 'ARS': '+54', 'PEN': '+51', 'MXN': '+52', 'CLP': '+56', 'PYG': '+595', 'USD': '+1'}
# orden en que se listan los países (el resto va al final)
COUNTRY_ORDER = ['COP', 'VES', 'USDEC', 'ARS', 'PEN', 'MXN', 'CLP', 'PYG', 'USD']
# país (texto guardado en Usuario.pais) → código de divisa
COUNTRY_TO_CURRENCY = {
    'Colombia': 'COP', 'Venezuela': 'VES', 'Ecuador': 'USDEC', 'Argentina': 'ARS', 'Perú': 'PEN',
    'México': 'MXN', 'Chile': 'CLP', 'Paraguay': 'PYG', 'Estados Unidos': 'USD',
}

STEPS = [
    {'n': '01', 'title': 'Elige tu juego', 'desc': 'Escoge entre cuenta primaria o secundaria según cómo juegas.'},
    {'n': '02', 'title': 'Paga como prefieras', 'desc': 'Mercado Pago, PayPal o directo por WhatsApp.'},
    {'n': '03', 'title': 'Recíbelo en minutos', 'desc': 'Te enviamos los datos y te ayudamos a instalar. Garantía de 1 año.'},
]

GIFT_STEPS = [
    {'n': '01', 'title': 'Compra tu código', 'desc': 'Elige el valor y paga como prefieras.'},
    {'n': '02', 'title': 'Recíbelo en minutos', 'desc': 'Te llega por WhatsApp o correo.'},
    {'n': '03', 'title': 'Canjéalo', 'desc': 'En PlayStation Store entra a Canjear códigos e ingrésalo.'},
]

COMPARE = [
    {'label': 'Usuario con el que juegas', 'p': 'El tuyo', 's': 'El que te damos', 'p_ok': True, 's_ok': False},
    {'label': 'Jugar sin internet', 'p': 'Sí', 's': 'No', 'p_ok': True, 's_ok': False},
    {'label': 'Otros usuarios de tu consola', 'p': 'También juegan', 's': 'No pueden', 'p_ok': True, 's_ok': False},
    {'label': 'Trofeos', 'p': 'En tu perfil', 's': 'En el perfil entregado', 'p_ok': True, 's_ok': False},
    {'label': 'Garantía', 'p': '1 año', 's': '1 año', 'p_ok': True, 's_ok': True},
]

FAQ = [
    {'q': '¿Cuál es la diferencia entre cuenta primaria y secundaria?', 'a': 'Con la primaria juegas desde tu propio perfil, con o sin internet, y los trofeos quedan en tu cuenta. La secundaria es más barata: juegas desde el perfil que te pasamos y siempre necesitas internet.'},
    {'q': '¿Los juegos son originales?', 'a': 'Sí. Son cuentas digitales compradas en PlayStation Store. No vendemos copias ni códigos no oficiales.'},
    {'q': '¿Tengo garantía?', 'a': 'Sí, un año sobre la cuenta. Si algo falla, lo resolvemos por WhatsApp.'},
    {'q': '¿Cómo me llega la cuenta?', 'a': 'Te enviamos las credenciales y un instructivo paso a paso por WhatsApp o correo. Si algo no queda claro, te acompañamos.'},
    {'q': '¿Cuánto tarda la entrega?', 'a': 'Entre 5 y 15 minutos después de validar tu pago, en horario de 10 a 20 h, todos los días.'},
    {'q': '¿Qué métodos de pago aceptan?', 'a': 'Mercado Pago (tarjeta, PSE, Nequi o Efecty), PayPal, o coordinando el pago directamente por WhatsApp.'},
    {'q': '¿Puedo comprar desde otro país?', 'a': 'Sí. Vendemos en {countries}. Elige tu país en el menú para ver los precios en tu moneda.'},
]

HELP_ISSUES = [
    {'key': 'no-llego', 'label': 'No me llegó la cuenta', 'msg': 'Hola, compré un juego y todavía no me llega la cuenta. Mi pedido es de cuenta primaria.'},
    {'key': 'login', 'label': 'No puedo iniciar sesión', 'msg': 'Hola, no puedo iniciar sesión con la cuenta que me enviaron. ¿Me pueden ayudar?'},
    {'key': 'clave', 'label': 'Me pide cambiar la contraseña', 'msg': 'Hola, la consola me pide cambiar la contraseña de la cuenta. ¿Qué debo hacer?'},
    {'key': 'otro', 'label': 'Otro inconveniente', 'msg': 'Hola, tengo un inconveniente con mi compra.'},
]

REVIEWS_FALLBACK = [
    {'name': 'diego.cst.11', 'text': 'Paso de nuevo a comentar: ya es la segunda vez que les compro un juego. Sigo sin entender cómo consiguen precios tan bajos, pero se agradece mucho. Gracias, todo bien otra vez.'},
    {'name': 'carmelo_j96', 'text': 'Un amigo me los recomendó y compré Dragon Ball Z Kakarot. Funciona perfecto y la atención fue excelente; los recomiendo sin dudarlo.'},
    {'name': 'melissa_alvarez_2', 'text': 'Totalmente confiables: mi novio compró un juego y lo tuvo en la consola en menos tiempo del que le tomó pagarlo. Si buscan dónde comprar juegos para la Play, esta es la mejor opción.'},
    {'name': 'davismendoza78', 'text': 'Les compré tres Call of Duty a muy buen precio. Son muy confiables, los recomiendo mucho.'},
    {'name': 'luisalejandroriverachavez', 'text': 'Acabo de comprar The Last of Us Parte II y todo salió sin ningún problema. Muy rápidos y eficientes.'},
    {'name': 'yeixon.blanco', 'text': 'Confiables y muy recomendados: compré el FC 26 y ya lo tengo descargando.'},
]

LEGAL_UPDATED = '14 de octubre de 2026'

LEGAL_T = [
    ('Objeto', ['Estos términos regulan el uso del sitio de Ganga Juegos y la compra de los productos digitales que ofrecemos: juegos para PS4 y PS5, suscripciones PS Plus, combos y tarjetas de regalo PSN. Al realizar una compra aceptas estas condiciones.', 'Ganga Juegos es una tienda independiente y no está afiliada a Sony Interactive Entertainment. PlayStation, PS4, PS5, PS Plus y PSN son marcas de sus respectivos titulares.']),
    ('Productos digitales y tipos de cuenta', ['Los juegos se entregan como cuentas digitales originales. No vendemos discos, copias modificadas ni códigos no oficiales.', 'Cuenta primaria: el juego se activa como consola principal y puedes jugarlo desde tu propio usuario, con o sin conexión a internet. Cuenta secundaria: juegas desde el usuario que te entregamos y necesitas estar conectado a internet para jugar.', 'Antes de comprar, revisa la plataforma (PS4 o PS5) y el tipo de cuenta. Si tienes dudas, escríbenos y te ayudamos a elegir.']),
    ('Precios, monedas y pagos', ['Los precios se publican en pesos colombianos y se muestran convertidos a la moneda de tu país como referencia. El valor final cobrado puede variar según la tasa de cambio y las comisiones de la plataforma de pago que elijas.', 'Aceptamos pagos por Mercado Pago, PayPal y coordinados por WhatsApp. Tu pedido queda confirmado cuando el pago es aprobado. Los precios y promociones pueden cambiar sin previo aviso, pero respetamos el valor de los pedidos ya pagados.']),
    ('Entrega', ['Una vez confirmado el pago, enviamos los datos de acceso por WhatsApp o al correo registrado. La mayoría de pedidos se entregan en pocos minutos; en horas de alta demanda o fuera del horario de atención la entrega puede tardar más.', 'Es tu responsabilidad suministrar un número de WhatsApp y un correo correctos. Junto con la cuenta te enviamos las instrucciones de instalación.']),
    ('Garantía', ['Todas las compras tienen garantía de un año contado desde la entrega. La garantía cubre fallas de acceso a la cuenta que no hayan sido causadas por el cliente.', 'No cubre cambios de correo, contraseña o datos de la cuenta hechos por el cliente, cuentas compartidas con terceros, ni sanciones de PlayStation Network derivadas del mal uso. Para usarla, escríbenos por WhatsApp con tu número de pedido.']),
    ('Cambios y reembolsos', ['Por tratarse de productos digitales de entrega inmediata, una vez enviados los datos de acceso no se aceptan devoluciones, salvo en los casos cubiertos por la garantía o previstos por la ley aplicable.', 'Si no podemos entregar un producto, te devolvemos el 100% del valor por el mismo medio de pago. Puedes solicitar el cambio de un juego por otro de igual o mayor valor antes de que te lo entreguemos.']),
    ('Uso indebido de las cuentas', ['No está permitido cambiar las credenciales de la cuenta entregada, compartirla, revenderla ni activarla en más consolas de las indicadas. Tampoco se permite usarla para conductas que infrinjan las normas de PlayStation Network.', 'El incumplimiento de estas condiciones anula la garantía y puede implicar la suspensión del acceso sin derecho a reembolso.']),
    ('Contacto', ['Para preguntas sobre estos términos, tu pedido o la garantía, escríbenos por WhatsApp o al correo de soporte publicado en el sitio. Responderemos lo antes posible.']),
]

LEGAL_P = [
    ('Datos que recopilamos', ['Cuando creas una cuenta o haces un pedido recopilamos tu nombre, correo electrónico, número de WhatsApp, país e historial de compras. También registramos datos técnicos básicos de navegación, como el tipo de dispositivo y las páginas visitadas.', 'Los pagos se procesan a través de Mercado Pago y PayPal. Ganga Juegos no almacena los datos de tus tarjetas.']),
    ('Para qué usamos tus datos', ['Usamos tu información para procesar y entregar tus pedidos, darte soporte, aplicar la garantía, administrar tu saldo a favor y tu código de referido, y prevenir fraudes. Si lo autorizas, también para enviarte ofertas y novedades, algo que puedes cancelar cuando quieras.']),
    ('Con quién los compartimos', ['Solo compartimos los datos necesarios con proveedores que nos ayudan a operar: plataformas de pago, servicios de mensajería y correo, y alojamiento web. No vendemos ni alquilamos tu información a terceros.']),
    ('Tus derechos', ['Puedes conocer, actualizar, rectificar y solicitar la eliminación de tus datos, así como revocar la autorización para su tratamiento, de acuerdo con la Ley 1581 de 2012 de Colombia y las normas de protección de datos de tu país.', 'Para ejercer estos derechos escríbenos por los canales de contacto. Responderemos tu solicitud en los plazos que fija la ley.']),
    ('Cookies', ['Usamos cookies necesarias para mantener tu sesión, tu carrito y tu país seleccionado, y cookies de analítica para entender cómo se usa el sitio y mejorarlo. Puedes bloquearlas o eliminarlas desde la configuración de tu navegador, aunque algunas funciones podrían dejar de funcionar.']),
    ('Contacto', ['Si tienes preguntas sobre el tratamiento de tus datos, escríbenos por WhatsApp o al correo de soporte publicado en el sitio.']),
]
