import sqlite3
import unittest
from modules.services.order_service import OrderService, money, qr_url


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.executescript('''
            CREATE TABLE products (id INTEGER PRIMARY KEY, stock INTEGER);
            INSERT INTO products VALUES (1, 10);
            CREATE TABLE inventory_movements (id INTEGER PRIMARY KEY, product_id, movement_type,
                quantity_change, stock_before, stock_after, note);
            CREATE TABLE transactions (id INTEGER PRIMARY KEY, subtotal_amount, discount_percent,
                discount_amount, total_amount, payment_method);
            CREATE TABLE transaction_items (transaction_id, product_id, product_name, quantity, price, subtotal);
            CREATE TABLE delivery_orders (id INTEGER PRIMARY KEY, items, subtotal, discount, total, fee,
                recipient, phone, address, carrier, tracking, note, status DEFAULT 'Chờ giao', transaction_id, updated_at);
        ''')
        from modules.customer_returns_schema import migrate
        migrate(self.conn)
        self.service = OrderService(self.conn)
        self.items = [dict(product_id=1, name='Test', quantity=2, price=100001, subtotal=200002)]

    def tearDown(self):
        self.conn.close()

    def create(self):
        return self.service.create(self.items, 10, 'Khách', '0912345678', 'Hà Nội', 30000)

    def stock(self):
        return self.conn.execute('SELECT stock FROM products').fetchone()[0]

    def test_cod_lifecycle(self):
        order = self.create()
        self.assertEqual(self.stock(), 8)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0], 0)
        self.service.update(order, 'Đang giao', 'TRACK1')
        self.service.update(order, 'Đã giao', 'TRACK1')
        self.service.update(order, 'Đã thu COD', 'TRACK1', received_amount=210002)
        self.assertEqual(self.stock(), 8)
        self.assertEqual(self.conn.execute('SELECT total_amount FROM transactions').fetchone()[0], 180002)
        with self.assertRaises(ValueError):
            self.service.update(order, 'Đã thu COD')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0], 1)

    def test_cancel_restock_once(self):
        order = self.create()
        self.service.update(order, 'Đã hủy', note='Khách hủy')
        self.assertEqual(self.stock(), 10)
        with self.assertRaises(ValueError):
            self.service.update(order, 'Đã hủy')
        self.assertEqual(self.stock(), 10)

    def test_insufficient_stock_rolls_back(self):
        self.items.append(dict(self.items[0], quantity=20))
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(self.stock(), 10)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM delivery_orders').fetchone()[0], 0)

    def test_duplicate_product_rolls_back_partial_reservation(self):
        self.items = [dict(self.items[0], quantity=6)] * 2
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(self.stock(), 10)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM inventory_movements').fetchone()[0], 0)

    def test_cash_sale_rounding(self):
        result = self.service.sales.checkout(self.items, 200002, 10, 'Tiền mặt')
        self.assertEqual(result['total_amount'], 180002)
        self.assertEqual(self.stock(), 8)

    def test_qr_and_validation(self):
        url = qr_url('VCB', '123456789', 'NGUYEN VAN A', 100000, 'AB123')
        self.assertIn('amount=100000', url)
        self.assertIn('addInfo=AB123', url)
        for value in ('NaN', 'inf', '-1', '2.5', ''):
            with self.assertRaises(ValueError):
                money(value)
        for discount in ('nan', '-1', '101'):
            with self.assertRaises(ValueError):
                self.service.create(self.items, discount, 'A', '0912345678', 'HN')


if __name__ == '__main__':
    unittest.main()
