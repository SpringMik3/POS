class Product:
    def __init__(self, id, name, barcode, price, stock, category):
        self.id = id
        self.name = name
        self.barcode = barcode
        self.price = price
        self.stock = stock
        self.category = category

class Transaction:
    def __init__(
        self,
        id,
        total_amount,
        payment_method,
        transaction_date,
        subtotal_amount=None,
        discount_percent=0,
        discount_amount=0
    ):
        self.id = id
        self.subtotal_amount = total_amount if subtotal_amount is None else subtotal_amount
        self.discount_percent = discount_percent or 0
        self.discount_amount = discount_amount or 0
        self.total_amount = total_amount
        self.payment_method = payment_method
        self.transaction_date = transaction_date

class TransactionItem:
    def __init__(self, id, transaction_id, product_id, product_name, quantity, price, subtotal):
        self.id = id
        self.transaction_id = transaction_id
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.price = price
        self.subtotal = subtotal
