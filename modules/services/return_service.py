from decimal import Decimal, ROUND_HALF_UP
from modules.services.inventory_service import InventoryService


def rounded(value):
    return int(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


class ReturnService:
    def __init__(self, conn):
        self.conn = conn

    def sales(self, term=''):
        return self.conn.execute('''SELECT t.id,t.transaction_date,COALESCE(c.name,'Khách lẻ'),t.total_amount,
            COALESCE((SELECT -SUM(r.total_amount) FROM transactions r WHERE r.refund_of=t.id),0),t.payment_method
            FROM transactions t LEFT JOIN customers c ON c.id=t.customer_id
            WHERE t.refund_of IS NULL AND (CAST(t.id AS TEXT) LIKE ? OR c.name LIKE ? OR c.phone LIKE ?)
            ORDER BY t.id DESC LIMIT 200''', (f'%{term}%',)*3).fetchall()

    def lines(self, transaction_id):
        sale = self.conn.execute('SELECT total_amount,refund_of FROM transactions WHERE id=?', (transaction_id,)).fetchone()
        if not sale or sale[1] is not None:
            raise ValueError('Chỉ đổi trả từ giao dịch bán hàng gốc.')
        rows = self.conn.execute('''SELECT ti.id,ti.product_id,ti.product_name,ti.quantity,ti.price,ti.subtotal,
            COALESCE((SELECT SUM(quantity) FROM return_items WHERE original_item_id=ti.id),0)
            FROM transaction_items ti WHERE ti.transaction_id=? ORDER BY ti.id''', (transaction_id,)).fetchall()
        gross = sum(Decimal(str(r[5])) for r in rows)
        if not rows or any(r[3] <= 0 or r[5] < 0 for r in rows) or sale[0] < 0:
            raise ValueError('Chi tiết đơn cũ không hợp lệ để hoàn tự động.')
        prefix, previous = Decimal(0), 0
        result = []
        for row in rows:
            prefix += Decimal(str(row[5]))
            cumulative = rounded(Decimal(str(sale[0])) * prefix / gross) if gross else 0
            result.append(dict(id=row[0], product_id=row[1], name=row[2], quantity=row[3], price=row[4],
                               gross=row[5], returned=row[6], entitlement=cumulative-previous))
            previous = cumulative
        return result

    def quote(self, transaction_id, selections):
        lines = {r['id']: r for r in self.lines(transaction_id)}
        if not selections:
            raise ValueError('Chọn ít nhất một sản phẩm cần trả.')
        result = []
        seen = set()
        for item_id, selection in selections.items():
            if int(item_id) in seen:
                raise ValueError('Một dòng sản phẩm chỉ được chọn một lần.')
            seen.add(int(item_id))
            line = lines.get(int(item_id))
            try:
                qty = int(str(selection['quantity']))
            except (ValueError, TypeError):
                raise ValueError('Số lượng trả phải là số nguyên.')
            if not line or qty <= 0 or qty > line['quantity']-line['returned']:
                raise ValueError('Số lượng trả vượt số còn được trả của đơn gốc.')
            portion = Decimal(line['entitlement']) / line['quantity']
            amount = rounded(portion*(line['returned']+qty)) - rounded(portion*line['returned'])
            result.append(dict(line, return_qty=qty, amount=amount, restock=bool(selection.get('restock', True))))
        return result

    def refund(self, transaction_id, selections, method, reason, expected_total=None):
        if not reason.strip():
            raise ValueError('Nhập lý do đổi trả / hủy đơn.')
        if method not in ('Tiền mặt', 'Chuyển khoản', 'Thẻ'):
            raise ValueError('Chọn phương thức hoàn tiền thực tế.')
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            lines = self.quote(transaction_id, selections)
            total = sum(r['amount'] for r in lines)
            if expected_total is not None and total != expected_total:
                raise ValueError('Đơn vừa thay đổi. Đóng và mở lại phiếu để kiểm tra số tiền mới.')
            gross = sum(Decimal(str(r['gross']))*r['return_qty']/r['quantity'] for r in lines)
            customer_id = self.conn.execute('SELECT customer_id FROM transactions WHERE id=?', (transaction_id,)).fetchone()[0]
            refund_id = self.conn.execute('''INSERT INTO transactions(subtotal_amount,discount_percent,discount_amount,
                total_amount,payment_method,customer_id,refund_of,reason) VALUES(?,0,?,?,?,?,?,?)''',
                (-float(gross), -(float(gross)-total), -total, method, customer_id, transaction_id, reason.strip())).lastrowid
            for line in lines:
                self.conn.execute('INSERT INTO return_items(refund_id,original_item_id,quantity,amount,restock) VALUES(?,?,?,?,?)',
                    (refund_id, line['id'], line['return_qty'], line['amount'], int(line['restock'])))
                self.conn.execute('''INSERT INTO transaction_items(transaction_id,product_id,product_name,quantity,price,subtotal)
                    VALUES(?,?,?,?,?,?)''', (refund_id, line['product_id'], line['name'], -line['return_qty'], line['price'],
                                             -float(Decimal(str(line['gross']))*line['return_qty']/line['quantity'])))
                if line['restock']:
                    InventoryService(self.conn).increase_stock(line['product_id'], line['return_qty'],
                        note=f'Hoàn #{refund_id}, đơn gốc #{transaction_id}', commit=False)
            return refund_id, total
