"""COD reservations stay outside paid-sales reports until remittance is confirmed."""
import json
import math
import re
from urllib.parse import urlencode
from modules.services.sales_service import SalesService


def money(value):
    try:
        value = float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        raise ValueError('Vui lòng nhập số tiền hợp lệ.')
    if not math.isfinite(value) or value < 0 or value != round(value):
        raise ValueError('Số tiền phải là số nguyên đồng, không âm.')
    return int(value)


def qr_url(bank, account, name, amount, reference):
    if not re.fullmatch(r'[A-Za-z0-9]{2,30}', bank.strip()):
        raise ValueError('Nhập mã ngân hàng (ví dụ VCB, MB, TCB hoặc BIN).')
    if not re.fullmatch(r'[0-9]{6,19}', account.strip()) or not name.strip():
        raise ValueError('Nhập số tài khoản 6–19 chữ số và tên chủ tài khoản.')
    amount = money(amount)
    if amount <= 0:
        raise ValueError('Số tiền QR phải lớn hơn 0.')
    return (f'https://img.vietqr.io/image/{bank.strip()}-{account.strip()}-compact2.png?'
            + urlencode(dict(amount=amount, addInfo=reference, accountName=name.strip())))


class OrderService:
    TRANSITIONS = {
        'Chờ giao': ('Đang giao', 'Đã hủy'),
        'Đang giao': ('Đã giao', 'Giao thất bại'),
        'Giao thất bại': ('Đang giao', 'Chờ hoàn hàng'),
        'Đã giao': ('Đã thu COD', 'Chờ hoàn hàng'),
        'Chờ hoàn hàng': ('Đã hoàn hàng',),
    }
    def __init__(self, conn):
        self.conn = conn
        self.sales = SalesService(conn)

    def create(self, items, discount, recipient, phone, address, fee=0, carrier='', tracking='', note='', customer_id=None):
        if not recipient.strip() or not address.strip():
            raise ValueError('Đơn COD cần tên người nhận và địa chỉ giao hàng.')
        phone = re.sub(r'[\s.()-]', '', phone)
        if not re.fullmatch(r'(0\d{9}|\+84\d{9})', phone):
            raise ValueError('Số điện thoại nhận hàng không hợp lệ.')
        if not items or any(int(i['quantity']) <= 0 for i in items):
            raise ValueError('Giỏ hàng không hợp lệ.')
        fee = money(fee)
        subtotal = sum(money(i['price']) * int(i['quantity']) for i in items)
        percent = float(discount)
        if not math.isfinite(percent) or not 0 <= percent <= 100:
            raise ValueError('Giảm giá phải từ 0 đến 100%.')
        _, reduction, total = self.sales.calculate_discount(subtotal, percent)
        total = round(total)
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            self.sales.validate_cart_stock(items)
            if customer_id is not None and not self.conn.execute('SELECT id FROM customers WHERE id=?', (customer_id,)).fetchone():
                raise ValueError('Không tìm thấy khách hàng.')
            cursor = self.conn.execute('''INSERT INTO delivery_orders
                (items, subtotal, discount, total, fee, recipient, phone, address, carrier, tracking, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (json.dumps(items, ensure_ascii=False), subtotal, percent, total, fee,
                 recipient.strip(), phone, address.strip(), carrier.strip(), tracking.strip(), note.strip()))
            order_id = cursor.lastrowid
            self.conn.execute('UPDATE delivery_orders SET customer_id=? WHERE id=?', (customer_id, order_id))
            self.conn.execute('INSERT INTO order_events(order_id,new_status,note) VALUES(?,?,?)', (order_id, 'Chờ giao', 'Tạo đơn và giữ hàng'))
            for item in items:
                self.sales.inventory_service.decrease_stock(item['product_id'], item['quantity'],
                    movement_type='SALE', note=f'Giữ hàng COD #{order_id}')
        return order_id

    def update(self, order_id, status, tracking=None, carrier_fee=0, received_amount=None, note='', restock=True, carrier=None, shipping_note=None):
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            row = self.conn.execute('SELECT items, subtotal, discount, total, status,fee,customer_id,transaction_id FROM delivery_orders WHERE id=?', (order_id,)).fetchone()
            if not row:
                raise ValueError('Không tìm thấy đơn.')
            items, subtotal, percent, total, old, fee, customer_id, transaction_id = row
            if status not in self.TRANSITIONS.get(old, ()):
                raise ValueError('Chuyển trạng thái không hợp lệ hoặc đơn đã xử lý.')
            if status in ('Giao thất bại', 'Chờ hoàn hàng', 'Đã hủy', 'Đã hoàn hàng') and not note.strip():
                raise ValueError('Nhập lý do / ghi chú xử lý đơn.')
            if status == 'Đã thu COD':
                carrier_fee = money(carrier_fee)
                if received_amount is None:
                    raise ValueError('Nhập số tiền thực nhận từ hãng vận chuyển.')
                received_amount = money(received_amount)
                expected = total + fee - carrier_fee
                if received_amount != expected and not note.strip():
                    raise ValueError('Tiền nhận có chênh lệch. Nhập ghi chú đối soát trước khi xác nhận.')
                transaction_id = self.sales.add_transaction(subtotal, percent, subtotal-total, total, 'COD')
                self.sales.add_transaction_items(transaction_id, json.loads(items))
                self.conn.execute('UPDATE transactions SET customer_id=? WHERE id=?', (customer_id, transaction_id))
                self.conn.execute('''UPDATE delivery_orders SET carrier_fee=?,received_amount=?,settlement_note=?,settled_at=CURRENT_TIMESTAMP WHERE id=?''',
                                  (carrier_fee, received_amount, note.strip(), order_id))
            elif status in ('Đã hủy', 'Đã hoàn hàng'):
                if status == 'Đã hoàn hàng':
                    self.conn.execute('UPDATE delivery_orders SET carrier_fee=?,settlement_note=? WHERE id=?',
                                      (money(carrier_fee), note.strip(), order_id))
                for item in json.loads(items) if (restock or status == 'Đã hủy') else []:
                    self.sales.inventory_service.increase_stock(item['product_id'], item['quantity'],
                        note=f'Hoàn hàng COD #{order_id}', commit=False)
            self.conn.execute('UPDATE delivery_orders SET status=?, tracking=COALESCE(?,tracking), transaction_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                              (status, tracking.strip() if tracking is not None else None, transaction_id, order_id))
            self.conn.execute('UPDATE delivery_orders SET carrier=COALESCE(?,carrier),note=COALESCE(?,note) WHERE id=?',
                              (carrier.strip() if carrier is not None else None, shipping_note.strip() if shipping_note is not None else None, order_id))
            event_note = note.strip()
            if status == 'Đã hoàn hàng':
                event_note += ' | ' + ('Đã nhập lại kho' if restock else 'Hàng hỏng/mất, không nhập kho')
            if status == 'Đã thu COD':
                event_note += f' | Phí hãng: {carrier_fee}; thực nhận: {received_amount}; chênh lệch: {received_amount-expected}'
            self.conn.execute('INSERT INTO order_events(order_id,old_status,new_status,note) VALUES(?,?,?,?)', (order_id, old, status, event_note))

    def details(self, order_id):
        cursor = self.conn.execute('SELECT * FROM delivery_orders WHERE id=?', (order_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError('Không tìm thấy đơn giao hàng.')
        return dict(zip([c[0] for c in cursor.description], row))

    def save_tracking(self, order_id, carrier, tracking, note):
        with self.conn:
            current = self.details(order_id)
            self.conn.execute('UPDATE delivery_orders SET carrier=?,tracking=?,note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
                              (carrier.strip(), tracking.strip(), note.strip(), order_id))
            self.conn.execute('INSERT INTO order_events(order_id,old_status,new_status,note) VALUES(?,?,?,?)',
                              (order_id, current['status'], current['status'], f'Cập nhật vận đơn: {carrier.strip()} / {tracking.strip()} / {note.strip()}'))

    def history(self, order_id):
        return self.conn.execute('SELECT created_at,old_status,new_status,note FROM order_events WHERE order_id=? ORDER BY id DESC', (order_id,)).fetchall()

    def list_orders(self):
        return self.conn.execute('''SELECT id, recipient, phone, total+fee, status, carrier, tracking, address, note
            FROM delivery_orders ORDER BY id DESC''').fetchall()
