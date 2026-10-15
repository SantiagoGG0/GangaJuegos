SESSION_KEY = 'cart'

ACCOUNT_TYPES = ('primaria', 'secundaria')
ITEM_TYPES = ('juego', 'combo', 'plan', 'gift')


class Cart:
    """Carrito de compras vivo en la sesión de Django.

    Cada línea es un dict {"type": "juego"|"combo"|"plan"|"gift", "id": int,
    "qty": int, "acc": "primaria"|"secundaria"|""}. El tipo de cuenta (`acc`)
    se elige por producto en la ficha del juego — dos líneas del mismo juego
    con distinta cuenta son productos distintos. Agregar un producto ya
    presente (mismo tipo, id y cuenta) suma a su `qty`.
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(SESSION_KEY)
        if cart is None:
            cart = []
        # carritos guardados antes del rediseño no tenían cuenta por línea:
        # heredan el modo de precio global que tenía la sesión en ese momento.
        legacy_acc = 'secundaria' if self.session.get('price_mode') == 'Secundaria' else 'primaria'
        for line in cart:
            line.setdefault('qty', 1)
            if 'acc' not in line:
                line['acc'] = legacy_acc if line.get('type') in ('juego', 'combo') else ''
        self.session[SESSION_KEY] = cart
        self.items = cart

    def _find(self, item_type, item_id, acc):
        item_id = int(item_id)
        for line in self.items:
            if line['type'] == item_type and line['id'] == item_id and line.get('acc', '') == acc:
                return line
        return None

    def add(self, item_type, item_id, qty=1, acc=''):
        if item_type not in ('juego', 'combo'):
            acc = ''
        elif acc not in ACCOUNT_TYPES:
            acc = 'primaria'
        line = self._find(item_type, item_id, acc)
        if line:
            line['qty'] += qty
        else:
            self.items.append({'type': item_type, 'id': int(item_id), 'qty': qty, 'acc': acc})
        self.save()

    def set_qty(self, index, qty):
        if 0 <= index < len(self.items):
            if qty <= 0:
                self.items.pop(index)
            else:
                self.items[index]['qty'] = qty
            self.save()

    def remove(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.save()

    def clear(self):
        self.items = []
        self.save()

    def save(self):
        self.session[SESSION_KEY] = self.items
        self.session.modified = True

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return sum(line.get('qty', 1) for line in self.items)
