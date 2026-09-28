import tempfile
import unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from modules.database import Database
from modules.customer_returns_schema import migrate
from modules.services.customer_service import CustomerService
from modules.services.return_service import ReturnService
from modules.services.order_service import OrderService
from modules.services.sales_service import SalesService
from modules.report_exporter import ReportDataService


class CustomerReturnsCODTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.folder.name)/'shop.db')
        self.conn = self.db.conn
        self.conn.executemany('INSERT INTO products(name,price,stock) VALUES(?,?,?)', [('Kem dưỡng',10001,10),('Son',99,10)])
        self.conn.commit()
        self.customers = CustomerService(self.conn)
        self.customer = self.customers.save('Khách thử', '+84 912345678', 'Địa chỉ thử', 'Khách quen')
        self.returns = ReturnService(self.conn)
        self.orders = OrderService(self.conn)
        self.items = [dict(product_id=1,name='Kem dưỡng',quantity=3,price=10001,subtotal=30003),
                      dict(product_id=2,name='Son',quantity=1,price=99,subtotal=99)]

    def tearDown(self):
        self.db.close()
        self.folder.cleanup()

    def sale(self):
        return SalesService(self.conn).checkout(self.items,30102,7,'Tiền mặt',self.customer)

    def order(self):
        return self.orders.create(self.items,7,'Khách thử','0912345678','Địa chỉ',30000,customer_id=self.customer)

    def test_customer_uniqueness_update_and_migration(self):
        with self.assertRaises(ValueError):
            self.customers.save('Trùng','0912345678')
        self.customers.save('Tên mới','0912345678','Mới','',self.customer)
        self.assertEqual(self.customers.get(self.customer)[1], 'Tên mới')
        self.assertEqual(len(self.customers.list('TÊN MỚI')),1)
        migrate(self.conn)
        migrate(self.conn)
        self.assertEqual(self.customers.get(self.customer)[2],'0912345678')

    def test_partial_returns_rounding_and_customer_net(self):
        sale = self.sale(); sale_id = sale['transaction_id']
        original = self.conn.execute('SELECT subtotal_amount,total_amount FROM transactions WHERE id=?',(sale_id,)).fetchone()
        refunded = 0
        for line in self.returns.lines(sale_id):
            for _ in range(line['quantity']):
                _, amount = self.returns.refund(sale_id,{line['id']:dict(quantity=1,restock=True)},'Tiền mặt','Khách trả')
                refunded += amount
        self.assertEqual(refunded,sale['total_amount'])
        self.assertEqual(self.conn.execute('SELECT stock FROM products WHERE id=1').fetchone()[0],10)
        self.assertEqual(self.conn.execute('SELECT subtotal_amount,total_amount FROM transactions WHERE id=?',(sale_id,)).fetchone(),original)
        self.assertEqual(self.customers.list()[0][-1],0)
        with self.assertRaises(ValueError):
            self.returns.refund(sale_id,{self.returns.lines(sale_id)[0]['id']:dict(quantity=1)},'Tiền mặt','Trả tiếp')
        report = ReportDataService(self.conn)
        result = report.get_summary(report.build_range_period('2000-01-01','2100-01-01'))
        self.assertEqual(result['total_revenue'],0)
        self.assertEqual(result['sale_count'],1)
        self.assertEqual(result['refund_count'],4)
        self.assertEqual(result['refunded_amount'],sale['total_amount'])

    def test_bad_quantity_and_deleted_product_rollback(self):
        sale = self.sale()['transaction_id']; line = self.returns.lines(sale)[0]
        for qty in ('1.5',0,4):
            with self.assertRaises(ValueError):
                self.returns.refund(sale,{line['id']:dict(quantity=qty)},'Tiền mặt','Lý do')
        with self.assertRaises(ValueError):
            self.returns.quote(sale,{line['id']:dict(quantity=2),str(line['id']):dict(quantity=2)})
        self.conn.execute('DELETE FROM products WHERE id=1'); self.conn.commit()
        with self.assertRaises(ValueError):
            self.returns.refund(sale,{line['id']:dict(quantity=1)},'Tiền mặt','Lý do')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0],1)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM return_items').fetchone()[0],0)
        self.returns.refund(sale,{line['id']:dict(quantity=1,restock=False)},'Chuyển khoản','Hàng hỏng')

    def test_refund_period_and_exchange_link(self):
        sale = self.sale()['transaction_id']; line = self.returns.lines(sale)[0]
        self.conn.execute("UPDATE transactions SET transaction_date='2025-01-01' WHERE id=?",(sale,)); self.conn.commit()
        refund_id,total = self.returns.refund(sale,{line['id']:dict(quantity=1,restock=False)},'Thẻ','Đổi hàng')
        self.assertEqual(self.conn.execute('SELECT stock FROM products WHERE id=1').fetchone()[0],7)
        report = ReportDataService(self.conn)
        self.assertEqual(report.get_summary(report.build_range_period('2025-01-01','2025-01-01'))['refund_count'],0)
        new_sale = SalesService(self.conn).checkout([self.items[1]],99,0,'Tiền mặt',self.customer,exchange_for=sale)
        self.assertEqual(self.conn.execute('SELECT exchange_for FROM transactions WHERE id=?',(new_sale['transaction_id'],)).fetchone()[0],sale)

    def test_cod_failed_return_and_double_processing(self):
        order = self.order()
        for state,note in [('Đang giao',''),('Giao thất bại','Không liên lạc được'),('Chờ hoàn hàng','Khách hủy')]:
            self.orders.update(order,state,note=note)
        self.assertEqual(self.conn.execute('SELECT stock FROM products WHERE id=1').fetchone()[0],7)
        self.orders.update(order,'Đã hoàn hàng',carrier_fee=15000,note='Hàng đã về')
        self.assertEqual(self.conn.execute('SELECT stock FROM products WHERE id=1').fetchone()[0],10)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0],0)
        with self.assertRaises(ValueError):
            self.orders.update(order,'Đã hoàn hàng',note='Lặp')
        self.assertEqual(len(self.orders.history(order)),5)

    def test_cod_settlement_difference_and_refund(self):
        order = self.order()
        self.orders.save_tracking(order,'Hãng thử','VD001','Gọi trước')
        for state in ('Đang giao','Đã giao'):
            self.orders.update(order,state)
        with self.assertRaises(ValueError):
            self.orders.update(order,'Đã thu COD',carrier_fee=20000,received_amount=1)
        self.assertEqual(self.orders.details(order)['status'],'Đã giao')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0],0)
        expected = self.orders.details(order)['total']+10000
        self.orders.update(order,'Đã thu COD',carrier_fee=20000,received_amount=expected-500,note='Hãng giữ 500 cần đối chiếu')
        data = self.orders.details(order)
        self.assertEqual(data['tracking'],'VD001')
        self.assertEqual(data['received_amount'],expected-500)
        with self.assertRaises(ValueError):
            self.orders.update(order,'Đã thu COD',received_amount=expected)
        self.assertEqual(len(self.customers.history(self.customer)),1)
        line = self.returns.lines(data['transaction_id'])[0]
        self.returns.refund(data['transaction_id'],{line['id']:dict(quantity=1,restock=True)},'Tiền mặt','Trả sau đối soát')
        self.assertEqual(self.orders.details(order)['status'],'Đã thu COD')

    def test_ui_checkout_customer_and_operation_dialogs(self):
        from modules.ui_sales import SalesPanel
        from modules.ui_checkout import CheckoutWindow
        from modules.ui_customer_orders import CustomerOrdersPanel, CodPanel
        from modules.styles import COLORS
        root = tk.Tk(); root.withdraw()
        callbacks = []
        root.report_callback_exception = lambda *args: callbacks.append(args)
        try:
            sales_frame = tk.Frame(root)
            panel = SalesPanel(sales_frame,self.db,COLORS)
            panel._add_product_to_cart(1,'Kem dưỡng',10001,10)
            checkout = CheckoutWindow(panel); checkout.withdraw()
            checkout.reload_customers(self.customer)
            self.assertEqual(checkout.vars['phone'].get(),'0912345678')
            with patch('modules.ui_checkout.messagebox.showinfo'),patch.object(panel.printer,'print_receipt',return_value=(True,'')):
                checkout.complete()
            self.assertEqual(len(self.customers.history(self.customer)),1)
            operations = CustomerOrdersPanel(tk.Frame(root),self.db)
            operations.sale_tree.selection_set(operations.sale_tree.get_children()[0])
            operations.open_return(); root.update_idletasks()
            for window in root.winfo_children():
                if isinstance(window,tk.Toplevel): window.destroy()
            order = self.order()
            cod = CodPanel(tk.Frame(root),self.db)
            cod.order_tree.selection_set(str(order)); cod.open_order()
            root.update_idletasks()
            self.assertFalse(callbacks)
        finally:
            root.destroy()


if __name__=='__main__': unittest.main()
