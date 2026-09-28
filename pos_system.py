# pos_system.py
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.database import Database
from modules.backup_service import BackupService
from modules.app_logger import get_logger
from modules.ui_sales import SalesPanel
from modules.ui_management import ManagementPanel
from modules.ui_report import ReportPanel
from modules.ui_tax import TaxPanel
from modules.ui_customer_orders import CustomerOrdersPanel, CodPanel
from modules.styles import COLORS


logger = get_logger(__name__)

class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AnnaBeauty POS System")
        self.root.geometry("1400x850")
        self.root.state('zoomed')
        
        self.colors = COLORS.copy()
        self.root.configure(bg=COLORS['background'])
        self.root.minsize(1100, 700)
        self.db = Database()
        self.setup_styles()
        self.create_header()
        
        main_container = tk.Frame(self.root, bg=self.colors['light'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(main_container, style='Modern.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        sales_tab = tk.Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(sales_tab, text='  💰 BÁN HÀNG  ')
        self.sales_panel = SalesPanel(sales_tab, self.db, self.colors)
        
        management_tab = tk.Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(management_tab, text='  SẢN PHẨM  ')
        self.management_panel = ManagementPanel(management_tab, self.db, self.colors)
        
        report_tab = tk.Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(report_tab, text='  THỐNG KÊ  ')
        self.report_panel = ReportPanel(report_tab, self.db, self.colors)

        tax_tab = tk.Frame(self.notebook, bg=COLORS['background'])
        self.notebook.add(tax_tab, text='  HỖ TRỢ KHAI THUẾ  ')
        self.tax_panel = TaxPanel(tax_tab, self.db, self.colors)
        operations_tab = tk.Frame(self.notebook, bg=COLORS['background'])
        self.notebook.add(operations_tab, text='  KHÁCH HÀNG & ĐỔI TRẢ  ')
        self.operations_panel = CustomerOrdersPanel(operations_tab, self.db, self.start_exchange)
        cod_tab = tk.Frame(self.notebook, bg=COLORS['background'])
        self.notebook.add(cod_tab, text='  ĐƠN COD  ')
        self.cod_panel = CodPanel(cod_tab, self.db)
        self.notebook.bind('<<NotebookTabChanged>>', self.refresh_active_tab)
        
        self.create_footer()

    def refresh_active_tab(self, event=None):
        index = self.notebook.index(self.notebook.select())
        if index == 0:
            self.sales_panel.search_products()
        elif index == 1:
            self.management_panel.load_categories()
            self.management_panel.load_products()
        elif index == 2:
            self.report_panel.refresh_report()
        elif index == 3:
            self.tax_panel.refresh()
        elif index == 4:
            self.operations_panel.refresh()
        elif index == 5:
            self.cod_panel.refresh()

    def start_exchange(self, original_id, check_only=False):
        if self.sales_panel.cart_tree.get_children():
            messagebox.showinfo('Giỏ hàng đang có sản phẩm', 'Hoàn tất hoặc xóa giỏ hàng hiện tại trước khi lập đơn đổi.')
            return False
        if check_only:
            return True
        self.sales_panel.exchange_for = original_id
        self.notebook.select(0)
        self.sales_panel._set_action_status(f'Đơn đổi từ #{original_id}: chọn hàng mới rồi thanh toán. Tiền hoàn đơn cũ đã ghi riêng.', 'success')
        return True
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Modern.TNotebook', 
                       background=self.colors['light'],
                       borderwidth=0)
        style.configure('Modern.TNotebook.Tab',
                       background=self.colors['white'],
                       foreground=self.colors['text_dark'],
                       padding=[14, 8],
                       font=('Segoe UI', 10, 'bold'),
                       borderwidth=0)
        style.map('Modern.TNotebook.Tab',
                 background=[('selected', self.colors['primary'])],
                 foreground=[('selected', self.colors['white'])],
                 expand=[('selected', [1, 1, 1, 0])])
    
    def create_header(self):
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=76)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        left_frame = tk.Frame(header_frame, bg=self.colors['primary'])
        left_frame.pack(side=tk.LEFT, padx=18, pady=10)
        
        tk.Label(left_frame, 
                text="🏪 AnnaBeauty", 
                font=('Segoe UI', 20, 'bold'),
                bg=self.colors['primary'],
                fg=self.colors['white']).pack(side=tk.LEFT)
        
        tk.Label(left_frame,
                text="POS System",
                font=('Segoe UI', 10),
                bg=self.colors['primary'],
                fg='#E3F2FD').pack(side=tk.LEFT, padx=10)
        
        right_frame = tk.Frame(header_frame, bg=self.colors['primary'])
        right_frame.pack(side=tk.RIGHT, padx=18)

        tk.Button(right_frame,
                text="💾 Backup DB",
                command=self.backup_database,
                font=('Segoe UI', 9, 'bold'),
                bg=self.colors['success'],
                fg=self.colors['white'],
                activebackground='#2e7d32',
                activeforeground=self.colors['white'],
                relief='solid',
                borderwidth=1,
                padx=10,
                pady=3,
                cursor='hand2').pack(anchor='e', pady=(0, 2))
        
        from datetime import datetime
        date_str = datetime.now().strftime('%d/%m/%Y - %H:%M')
        
        tk.Label(right_frame,
                text=date_str,
                font=('Segoe UI', 10),
                bg=self.colors['primary'],
                fg=self.colors['white']).pack(anchor='e')
        
        tk.Label(right_frame,
                text="👤 Admin",
                font=('Segoe UI', 10),
                bg=self.colors['primary'],
                fg='#E3F2FD').pack(anchor='e')

    def backup_database(self):
        try:
            self.db.conn.commit()
            backup_path = BackupService(self.db.db_path).backup_database(reason="manual")
            messagebox.showinfo("Backup thành công", f"Đã backup database:\n{backup_path}")
            backup_name = backup_path.name if hasattr(backup_path, 'name') else str(backup_path)
            self.set_status(f"Backup xong: {backup_name}", is_error=False)
        except Exception as exc:
            logger.exception("Manual database backup failed")
            messagebox.showerror("Backup lỗi", f"Không thể backup database:\n{exc}")
            self.set_status("Backup lỗi", is_error=True)

    def set_status(self, message, is_error=False):
        if hasattr(self, 'footer_label'):
            default_text = "© 2025 AnnaBeauty POS System - Phiên bản 2.0"
            self.footer_label.config(
                text=message,
                fg=self.colors['danger'] if is_error else self.colors['white'],
            )
            self.root.after(6000, lambda: self.footer_label.config(text=default_text, fg=self.colors['white']))
    
    def create_footer(self):
        footer = tk.Frame(self.root, bg=self.colors['secondary'], height=28)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        self.footer_label = tk.Label(footer,
                text="© 2025 AnnaBeauty POS System - Phiên bản 2.0",
                font=('Segoe UI', 8),
                bg=self.colors['secondary'],
                fg=self.colors['white'])
        self.footer_label.pack(pady=5)
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

def main():
    root = tk.Tk()
    app = POSApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
