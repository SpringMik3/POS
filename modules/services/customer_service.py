import re
import sqlite3


class CustomerService:
    def __init__(self, conn):
        self.conn = conn

    def save(self, name, phone='', address='', note='', customer_id=None):
        name = name.strip()
        phone = re.sub(r'[\s.()-]', '', phone)
        if phone.startswith('+84'):
            phone = '0' + phone[3:]
        if not name:
            raise ValueError('Nhập tên khách hàng.')
        if phone and not re.fullmatch(r'0\d{9}', phone):
            raise ValueError('Điện thoại cần 10 chữ số, bắt đầu bằng 0; hoặc để trống.')
        try:
            with self.conn:
                if customer_id is None:
                    return self.conn.execute('INSERT INTO customers(name,phone,address,note) VALUES(?,?,?,?)',
                        (name, phone or None, address.strip(), note.strip())).lastrowid
                cursor = self.conn.execute('UPDATE customers SET name=?,phone=?,address=?,note=? WHERE id=?',
                    (name, phone or None, address.strip(), note.strip(), customer_id))
                if cursor.rowcount != 1:
                    raise ValueError('Không tìm thấy khách hàng.')
                return customer_id
        except sqlite3.IntegrityError:
            raise ValueError('Điện thoại này đã có trong danh sách khách hàng.')

    def list(self, term=''):
        rows = self.conn.execute('''SELECT c.id,c.name,COALESCE(c.phone,''),c.address,c.note,
            (SELECT COUNT(*) FROM transactions t WHERE t.customer_id=c.id AND t.refund_of IS NULL),
            COALESCE((SELECT SUM(total_amount) FROM transactions t WHERE t.customer_id=c.id),0)
            FROM customers c ORDER BY c.name''').fetchall()
        term = term.strip().casefold()
        return [r for r in rows if not term or term in f'{r[1]} {r[2]}'.casefold()]

    def get(self, customer_id):
        return self.conn.execute('SELECT id,name,phone,address,note FROM customers WHERE id=?', (customer_id,)).fetchone()

    def history(self, customer_id):
        return self.conn.execute('''SELECT id,transaction_date,
            CASE WHEN refund_of IS NOT NULL THEN 'Hoàn #'||refund_of
                 WHEN exchange_for IS NOT NULL THEN 'Đổi từ #'||exchange_for ELSE 'Bán hàng' END,
            total_amount,payment_method FROM transactions WHERE customer_id=? ORDER BY id DESC''', (customer_id,)).fetchall()
