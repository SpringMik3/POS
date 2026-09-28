import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

from modules.database import Database
from modules.services.tax_service import TaxService


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.folder.name) / 'test.db')
        self.db.conn.executemany('INSERT INTO transactions(total_amount, subtotal_amount, discount_amount, payment_method, transaction_date) VALUES(?,?,?,?,?)', [
            (90, 100, 10, 'Tiền mặt', '2026-01-01 00:00:00'),
            (200, 200, 0, 'COD', '2026-01-31 23:59:59'),
            (500, 500, 0, 'Thẻ', '2026-02-01 00:00:00')])
        self.db.conn.commit()

    def tearDown(self):
        self.db.close()
        self.folder.cleanup()

    def test_tax_period_profile_and_export(self):
        service = TaxService(self.db.conn)
        service.save_profile({'name': '<Cửa hàng>', 'tax_id': '0012345678'})
        self.assertEqual(TaxService(self.db.conn).load_profile()['tax_id'], '0012345678')
        data = service.collect('2026-01-01', '2026-01-31')
        self.assertEqual(data['summary']['total_revenue'], 290)
        self.assertEqual(data['summary']['transaction_count'], 2)
        self.assertEqual(len(data['transactions']), 2)
        self.db.conn.execute("INSERT INTO delivery_orders(items,subtotal,discount,total,recipient,phone,address,status) VALUES('[]',700,0,700,'Test','0123456789','Test','Đã giao')")
        self.db.conn.commit()
        with_pending = service.collect('2026-01-01', '2026-01-31')
        self.assertEqual(with_pending['summary']['total_revenue'], 290)
        self.assertEqual(with_pending['pending'][0][2], 700)
        html = service.render_html(data, service.load_profile(), '<script>alert(1)</script>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;Cửa hàng&gt;', html)
        self.assertEqual(service.reports.get_daily_revenue(service.reports.build_range_period('2026-01-01', '2026-01-31')), [('2026-01-01', 90.0), ('2026-01-31', 200.0)])
        for start, end in [('', ''), ('2026-02-01', '2026-01-01'), ('2026-02-30', '2026-03-01')]:
            with self.assertRaises(ValueError):
                service.collect(start, end)

    def test_new_panels_and_product_filters(self):
        from pos_system import POSApp
        self.db.conn.executemany('INSERT INTO products(name,price,stock) VALUES(?,?,?)', [('Hết', 100, 0), ('Sắp hết', 100, 5), ('Còn', 100, 20)])
        self.db.conn.commit()
        root = tk.Tk()
        root.withdraw()
        try:
            with patch('pos_system.Database', return_value=self.db):
                app = POSApp(root)
            root.update_idletasks()
            self.assertEqual(len(app.notebook.tabs()), 6)
            self.assertEqual(len(app.operations_panel.tabs.tabs()), 2)
            self.assertEqual(app.notebook.tab(5, 'text').strip(), 'ĐƠN COD')
            self.assertFalse(hasattr(app.operations_panel, 'order_tree'))
            self.assertEqual(len(app.report_panel.sections.tabs()), 2)
            panel = app.management_panel
            panel.stock_filter.set('Hết hàng')
            panel.load_products()
            self.assertEqual(len(panel.products_tree.get_children()), 1)
            panel.reset_product_filters()
            self.assertEqual(len(panel.products_tree.get_children()), 3)
            for index in range(6):
                app.notebook.select(index)
                app.refresh_active_tab()
                root.update_idletasks()
            app.tax_panel.start.set('2026-01-01')
            app.tax_panel.end.set('2026-01-31')
            self.assertEqual(app.tax_panel.refresh()['summary']['total_revenue'], 290)
            app.tax_panel.start.set('bad')
            self.assertIsNone(app.tax_panel.refresh())
            self.assertFalse(app.tax_panel.tree.get_children())
            self.assertLess(app.management_panel.parent.winfo_reqwidth(), 1400)
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
