"""Construct real Tk widgets with a disposable database; no production data or printing."""
import tempfile
import unittest
from pathlib import Path
import tkinter as tk
from unittest.mock import patch

from modules.database import Database
from modules.ui_sales import SalesPanel
from modules.ui_checkout import CheckoutWindow
from modules.styles import COLORS


class CheckoutUITests(unittest.TestCase):
    def test_payment_modes_and_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / 'test.db')
            db.conn.execute("INSERT INTO products (name, barcode, price, stock) VALUES ('Test', '123', 100000, 10)")
            db.conn.commit()
            root = None
            try:
                root = tk.Tk()
                root.withdraw()
                panel = SalesPanel(root, db, COLORS)
                panel._add_product_to_cart(1, 'Test', 100000, 10)
                window = CheckoutWindow(panel)
                window.withdraw()
                root.update_idletasks()
                for method in ('COD', 'Chuyển khoản', 'Thẻ', 'Tiền mặt'):
                    window.vars['method'].set(method)
                    root.update_idletasks()
                    self.assertEqual(window.totals()[1], 100000)
                window.vars['cash'].set('50000')
                with patch('modules.ui_checkout.messagebox.showerror') as error:
                    window.complete()
                    error.assert_called_once()
                self.assertEqual(db.conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0], 0)
                window.vars['cash'].set('100000')
                with patch('modules.ui_checkout.messagebox.showinfo'), patch.object(panel.printer, 'print_receipt', side_effect=RuntimeError('Printer offline')):
                    window.complete()
                self.assertFalse(panel.cart_tree.get_children())
                self.assertEqual(db.conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0], 1)
                root.update_idletasks()
            finally:
                if root is not None:
                    root.destroy()
                db.close()


if __name__ == '__main__':
    unittest.main()
