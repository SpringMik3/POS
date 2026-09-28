from modules.app_logger import get_logger
from modules.services.inventory_service import InventoryService


logger = get_logger(__name__)


class SalesService:
    def __init__(self, conn, inventory_service=None):
        self.conn = conn
        self.inventory_service = inventory_service or InventoryService(conn)

    def calculate_discount(self, subtotal_amount, discount_percent):
        """Calculate discount values with percent constrained to 0..100."""
        subtotal = float(subtotal_amount or 0)
        try:
            percent = float(discount_percent or 0)
        except (TypeError, ValueError):
            percent = 0

        percent = max(0, min(percent, 100))
        discount_amount = subtotal * percent / 100
        total_amount = max(subtotal - discount_amount, 0)
        return percent, discount_amount, total_amount

    def validate_cart_stock(self, cart_items):
        """Validate every cart item against current product stock."""
        for item in cart_items:
            self.inventory_service.validate_stock_available(
                item['product_id'],
                item['quantity'],
                item.get('name'),
            )

    def add_transaction(self, subtotal_amount, discount_percent, discount_amount, total_amount, payment_method):
        """Insert a transaction row and return its id."""
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            INSERT INTO transactions (
                subtotal_amount,
                discount_percent,
                discount_amount,
                total_amount,
                payment_method
            )
            VALUES (?, ?, ?, ?, ?)
            ''',
            (subtotal_amount, discount_percent, discount_amount, total_amount, payment_method),
        )
        return cursor.lastrowid

    def add_transaction_items(self, transaction_id, cart_items):
        """Insert all transaction item rows for a transaction."""
        cursor = self.conn.cursor()
        for item in cart_items:
            cursor.execute(
                '''
                INSERT INTO transaction_items (
                    transaction_id,
                    product_id,
                    product_name,
                    quantity,
                    price,
                    subtotal
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    int(transaction_id),
                    int(item['product_id']),
                    item['name'],
                    int(item['quantity']),
                    float(item['price']),
                    float(item['subtotal']),
                ),
            )

    def checkout(self, cart_items, subtotal_amount, discount_percent, payment_method, customer_id=None, exchange_for=None):
        """Create a paid transaction, insert items, and decrease product stock."""
        percent, discount_amount, total_amount = self.calculate_discount(subtotal_amount, discount_percent)
        total_amount = round(total_amount)
        discount_amount = float(subtotal_amount) - total_amount

        try:
            if not cart_items or any(int(item['quantity']) <= 0 for item in cart_items):
                raise ValueError('Giỏ hàng không hợp lệ.')
            self.conn.execute('BEGIN IMMEDIATE')
            if customer_id is not None and not self.conn.execute('SELECT id FROM customers WHERE id=?', (customer_id,)).fetchone():
                raise ValueError('Khách hàng không còn tồn tại.')
            if exchange_for is not None and not self.conn.execute('SELECT id FROM transactions WHERE id=? AND refund_of IS NULL', (exchange_for,)).fetchone():
                raise ValueError('Không tìm thấy đơn gốc để đổi hàng.')
            self.validate_cart_stock(cart_items)
            transaction_id = self.add_transaction(
                subtotal_amount,
                percent,
                discount_amount,
                total_amount,
                payment_method,
            )
            self.add_transaction_items(transaction_id, cart_items)
            if customer_id is not None or exchange_for is not None:
                self.conn.execute('UPDATE transactions SET customer_id=?,exchange_for=? WHERE id=?',
                                  (customer_id, exchange_for, transaction_id))

            for item in cart_items:
                self.inventory_service.decrease_stock(
                    item['product_id'],
                    item['quantity'],
                    item.get('name'),
                    commit=False,
                    movement_type='SALE',
                    note=f"Transaction #{transaction_id}",
                )

            self.conn.commit()
            return {
                'transaction_id': transaction_id,
                'discount_percent': percent,
                'discount_amount': discount_amount,
                'total_amount': total_amount,
            }
        except Exception:
            self.conn.rollback()
            logger.exception("Sales checkout service failed")
            raise
