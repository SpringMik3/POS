# modules/ui_sales.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from modules.utils import format_currency
from modules.receipt_printer import ReceiptPrinter
from modules.app_logger import get_logger
from modules.services.inventory_service import InventoryService
from modules.services.product_service import ProductService
from modules.services.sales_service import SalesService


logger = get_logger(__name__)

class SalesPanel:
    LOW_STOCK_THRESHOLD = 10

    def __init__(self, parent, db, colors):
        self.parent = parent
        self.db = db
        self.colors = colors
        self.product_service = ProductService(self.db.conn)
        self.inventory_service = InventoryService(self.db.conn)
        self.sales_service = SalesService(self.db.conn, self.inventory_service)
        self.cart = []
        self.cart_items = {}
        self.total_amount = 0
        self.printer = ReceiptPrinter()
        self.setup_styles()
        self.create_widgets()
        self.load_products()
        self.scanning_active = True
        self.barcode_entry.focus_set()

    def setup_styles(self):
        from modules.styles import configure_treeview_style
        self.style = configure_treeview_style('Sales.Treeview', 'sales')

    def create_widgets(self):
        from modules.styles import COLORS, FONT, LAYOUT, button_style, card_style, entry_style, enable_treeview_sorting
        
        main_container = tk.Frame(self.parent, bg=COLORS['background'])
        main_container.pack(fill=tk.BOTH, expand=True)
        main_container.rowconfigure(1, weight=1)
        main_container.columnconfigure(0, weight=1)

        header_container = tk.Frame(main_container, bg=COLORS['primary'], height=LAYOUT['header_height'])
        header_container.grid(row=0, column=0, sticky='ew')
        header_container.pack_propagate(False)
        header = tk.Label(header_container, text="💰 BÁN HÀNG", font=FONT['header'], bg=COLORS['primary'], fg=COLORS['surface'])
        header.pack(expand=True)

        content = tk.Frame(main_container, bg=COLORS['background'])
        content.grid(row=1, column=0, sticky='nsew', padx=LAYOUT['page_padx'], pady=LAYOUT['page_pady'])
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=3, uniform='sales_cols')
        content.columnconfigure(1, weight=2, uniform='sales_cols')

        left = tk.Frame(content, bg=COLORS['background'])
        left.grid(row=0, column=0, sticky='nsew', padx=(0, LAYOUT['gap']))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        input_card = tk.Frame(left, **card_style(compact=True))
        input_card.grid(row=0, column=0, sticky='ew', pady=(0, LAYOUT['gap']))
        input_card.columnconfigure(1, weight=1)

        tk.Label(input_card, text="🔍 Quét mã vạch:", bg=COLORS['surface'], font=FONT['label'], fg=COLORS['text_primary']).grid(row=0, column=0, sticky='w', padx=(0, 8), pady=3)
        self.barcode_entry = tk.Entry(input_card, width=18, **entry_style('search', relief='flat'))
        self.barcode_entry.grid(row=0, column=1, sticky='ew', padx=(0, 8), pady=3)
        self.barcode_entry.bind('<Return>', self.on_barcode_scan)
        self.barcode_entry.bind('<FocusOut>', self._on_barcode_focus_out)
        tk.Button(input_card, text="Bắt đầu quét", command=self.activate_scanner,
                 **button_style('success', compact=True)).grid(row=0, column=2, sticky='ew', pady=3)
        self.scan_status = tk.Label(input_card, text="⚫ Sẵn sàng quét", bg=COLORS['surface'], fg=COLORS['success'], font=FONT['body_small'])
        self.scan_status.grid(row=1, column=1, columnspan=2, sticky='w', pady=(0, 4))
        
        tk.Label(input_card, text="🔎 Tìm sản phẩm:", bg=COLORS['surface'], font=FONT['label'], fg=COLORS['text_primary']).grid(row=2, column=0, sticky='w', padx=(0, 8), pady=3)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_products)
        self.search_entry = tk.Entry(input_card, textvariable=self.search_var, width=24, insertwidth=2, insertbackground='#000', **entry_style('search', relief='flat'))
        self.search_entry.grid(row=2, column=1, columnspan=2, sticky='ew', pady=3)
        self.search_entry.bind('<FocusIn>', self._on_search_focus_in)
        self.search_entry.bind('<Escape>', self._on_search_escape)

        products_card = tk.Frame(left, **card_style())
        products_card.grid(row=1, column=0, sticky='nsew')
        products_card.rowconfigure(1, weight=1)
        products_card.columnconfigure(0, weight=1)
        products_header = tk.Label(products_card, text="📃 DANH SÁCH SẢN PHẨM", font=FONT['subtitle'], bg=COLORS['surface'], fg=COLORS['text_primary'])
        products_header.grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['gap']))
        columns = ('ID', 'Tên sản phẩm', 'Giá', 'Tồn kho')
        tree_frame = tk.Frame(products_card, bg=COLORS['surface'])
        tree_frame.grid(row=1, column=0, sticky='nsew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.products_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', style='Sales.Treeview', height=10)
        for col in columns:
            self.products_tree.heading(col, text=col)
            if col == 'Tên sản phẩm':
                self.products_tree.column(col, width=220, minwidth=120, stretch=True)
            elif col == 'ID':
                self.products_tree.column(col, width=55, anchor='center', minwidth=40, stretch=False)
            else:
                self.products_tree.column(col, width=90, anchor='center', minwidth=70, stretch=False)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.products_tree.xview)
        self.products_tree.configure(xscrollcommand=hsb.set)
        self.products_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.products_tree.tag_configure('low_stock', background=COLORS['warning_light'], foreground=COLORS['text_primary'])
        self.products_tree.tag_configure('out_of_stock', background=COLORS['danger_light'], foreground=COLORS['text_primary'])
        enable_treeview_sorting(self.products_tree, numeric_columns={'ID', 'Giá', 'Tồn kho'})
        self.products_tree.bind('<Double-1>', self.add_to_cart)
        self.products_tree.bind('<Return>', self._handle_return)
        self.products_tree.bind('<Key-Return>', self._handle_return)
        self.products_tree.bind('<Button-1>', lambda e: self.products_tree.focus_set())

        right = tk.Frame(content, bg=COLORS['background'])
        right.grid(row=0, column=1, sticky='nsew')
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        cart_card = tk.Frame(right, **card_style())
        cart_card.grid(row=0, column=0, sticky='nsew')
        cart_card.rowconfigure(1, weight=1)
        cart_card.columnconfigure(0, weight=1)
        cart_header = tk.Label(cart_card, text="🛒 GIỎ HÀNG", font=FONT['subtitle'], bg=COLORS['surface'], fg=COLORS['text_primary'])
        cart_header.grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['gap']))
        cart_columns = ('Sản phẩm', 'SL', 'Đơn giá', 'Thành tiền')
        tree_cart_frame = tk.Frame(cart_card, bg=COLORS['surface'])
        tree_cart_frame.grid(row=1, column=0, sticky='nsew')
        tree_cart_frame.rowconfigure(0, weight=1)
        tree_cart_frame.columnconfigure(0, weight=1)
        self.cart_tree = ttk.Treeview(tree_cart_frame, columns=cart_columns, show='headings', style='Sales.Treeview', height=10)
        for col in cart_columns:
            self.cart_tree.heading(col, text=col)
            if col == 'Sản phẩm':
                self.cart_tree.column(col, width=170, minwidth=110, stretch=True)
            elif col == 'SL':
                self.cart_tree.column(col, width=55, anchor='center', minwidth=45, stretch=False)
            else:
                self.cart_tree.column(col, width=90, anchor='center', minwidth=75, stretch=False)
        vsb_cart = ttk.Scrollbar(tree_cart_frame, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=vsb_cart.set)
        hsb_cart = ttk.Scrollbar(tree_cart_frame, orient="horizontal", command=self.cart_tree.xview)
        self.cart_tree.configure(xscrollcommand=hsb_cart.set)
        self.cart_tree.grid(row=0, column=0, sticky='nsew')
        vsb_cart.grid(row=0, column=1, sticky='ns')
        hsb_cart.grid(row=1, column=0, sticky='ew')
        enable_treeview_sorting(self.cart_tree, numeric_columns={'SL', 'Đơn giá', 'Thành tiền'})
        self.cart_tree.bind('<Delete>', self.remove_from_cart)
        self.cart_tree.bind('<BackSpace>', self._handle_backspace)
        self.cart_tree.bind('<Key-BackSpace>', self._handle_backspace)
        self.cart_tree.bind('<Button-1>', lambda e: self.cart_tree.focus_set())

        total_card = tk.Frame(right, **card_style(compact=True))
        total_card.grid(row=1, column=0, sticky='ew', pady=(LAYOUT['gap'], 0))
        total_card.columnconfigure(0, weight=1)
        self.total_label = tk.Label(total_card, text="TỔNG TIỀN: 0 ₫", font=FONT['title'], bg=COLORS['surface'], fg=COLORS['primary'])
        self.total_label.grid(row=0, column=0, sticky='ew', pady=(0, LAYOUT['gap']))
        button_frame = tk.Frame(total_card, bg=COLORS['surface'])
        button_frame.grid(row=1, column=0, sticky='ew')
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        checkout_btn = tk.Button(button_frame, text="💳 THANH TOÁN", command=self.checkout,
                                **button_style('success', compact=True))
        checkout_btn.grid(row=0, column=0, sticky='ew', padx=(0, LAYOUT['small_gap']))
        clear_btn = tk.Button(button_frame, text="🗑️ XÓA GIỎ", command=self.clear_cart,
                             **button_style('danger', compact=True))
        clear_btn.grid(row=0, column=1, sticky='ew', padx=(LAYOUT['small_gap'], 0))
        self.action_status = tk.Label(
            total_card,
            text="",
            font=FONT['body_small'],
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            anchor='w'
        )
        self.action_status.grid(row=2, column=0, sticky='ew', pady=(6, 0))

    def _set_action_status(self, message, variant='info'):
        from modules.styles import COLORS
        colors = {
            'success': COLORS['success'],
            'danger': COLORS['danger'],
            'warning': COLORS['warning'],
            'info': COLORS['text_secondary'],
        }
        if hasattr(self, 'action_status'):
            self.action_status.config(text=message, fg=colors.get(variant, COLORS['text_secondary']))
            self.parent.after(6000, lambda: self.action_status.config(text=""))

    def _product_row_tags(self, stock):
        try:
            stock_value = int(stock)
        except (TypeError, ValueError):
            return ()

        if stock_value <= 0:
            return ('out_of_stock',)
        if stock_value < self.LOW_STOCK_THRESHOLD:
            return ('low_stock',)
        return ()

    def _handle_return(self, event):
        """Xử lý phím Return - thêm sản phẩm vào giỏ nếu danh sách được focus."""
        try:
            # Check nếu products_tree có focus hoặc selection
            if self.products_tree.selection():
                self.add_to_cart(event)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi thêm sản phẩm: {str(e)}")
            self._set_action_status("Lỗi khi thêm sản phẩm", 'danger')

    def _handle_backspace(self, event):
        """Xử lý phím Backspace - giảm số lượng sản phẩm trong giỏ."""
        try:
            # Check nếu cart_tree có selection
            if self.cart_tree.selection():
                self.decrease_cart_qty(event)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi giảm số lượng: {str(e)}")
            self._set_action_status("Lỗi khi giảm số lượng", 'danger')

    def _cart_iid(self, product_id):
        return f"product_{int(product_id)}"

    def _product_id_from_cart_iid(self, cart_iid):
        return int(str(cart_iid).replace("product_", "", 1))

    def _parse_money(self, value):
        if isinstance(value, str):
            return float(value.replace(',', ''))
        return float(value)

    def _add_product_to_cart(self, product_id, name, price, stock):
        product_id = int(product_id)
        stock = int(stock)
        price = self._parse_money(price)

        if stock <= 0:
            messagebox.showwarning("Hết hàng", f"Sản phẩm '{name}' đã hết hàng!")
            return

        cart_iid = self._cart_iid(product_id)
        if self.cart_tree.exists(cart_iid):
            values = self.cart_tree.item(cart_iid)['values']
            current_qty = int(values[1])
            if current_qty >= stock:
                messagebox.showwarning("Vượt quá tồn kho", f"Chỉ còn {stock} sản phẩm trong kho!")
                return

            new_qty = current_qty + 1
            subtotal = new_qty * price
            self.cart_tree.item(cart_iid, values=(name, new_qty, f"{price:,.0f}", f"{subtotal:,.0f}"))
            self.cart_items[product_id] = {
                'id': product_id,
                'name': name,
                'price': price,
                'stock': stock,
                'quantity': new_qty,
            }
            self.update_total()
            return

        self.cart_tree.insert('', 'end', iid=cart_iid, values=(name, 1, f"{price:,.0f}", f"{price:,.0f}"))
        self.cart_items[product_id] = {
            'id': product_id,
            'name': name,
            'price': price,
            'stock': stock,
            'quantity': 1,
        }
        self.update_total()

    def load_products(self):
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        products = self.product_service.get_products()
        for product in products:
            formatted_product = (product[0], product[1], f"{product[3]:,.0f}", product[4])
            self.products_tree.insert('', 'end', values=formatted_product, tags=self._product_row_tags(product[4]))

    def search_products(self, *args):
        """Tìm kiếm sản phẩm theo tên hoặc mã vạch (gộp chung)."""
        search_term = self.search_var.get().strip().lower()
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        
        if not search_term:
            # Nếu rỗng, nạp lại toàn bộ danh sách
            self.load_products()
            return
        
        products = self.product_service.search_products(search_term)
        for product in products:
            formatted_product = (product[0], product[1], f"{product[3]:,.0f}", product[4])
            self.products_tree.insert('', 'end', values=formatted_product, tags=self._product_row_tags(product[4]))

    def _on_search_focus_in(self, event):
        """Khi focus vào search, disable auto-focus barcode và cập nhật status."""
        from modules.styles import COLORS
        self.scanning_active = False
        self.scan_status.config(text="⭕ Chưa sẵn sàng quét", fg=COLORS['warning'])
        self.barcode_entry.config(bg=COLORS['background'])

    def _on_search_escape(self, event):
        """Khi nhấn Escape, clear search, enable lại quét và focus vào barcode."""
        from modules.styles import COLORS
        self.search_var.set("")
        self.scanning_active = True
        self.scan_status.config(text="⚫ Sẵn sàng quét", fg=COLORS['success'])
        self.barcode_entry.config(bg=COLORS['success_light'])
        self.barcode_entry.focus_set()

    def add_to_cart(self, event):
        selected = self.products_tree.selection()
        if not selected:
            return
        item = self.products_tree.item(selected[0])
        product_id, name, price_str, stock = item['values']
        self._add_product_to_cart(product_id, name, price_str, stock)

    def remove_from_cart(self, event):
        selected = self.cart_tree.selection()
        if selected:
            product_id = self._product_id_from_cart_iid(selected[0])
            self.cart_tree.delete(selected[0])
            self.cart_items.pop(product_id, None)
            self.update_total()

    def decrease_cart_qty(self, event):
        """Giảm số lượng sản phẩm trong giỏ khi bấm Backspace. Nếu = 1 thì xóa luôn."""
        selected = self.cart_tree.selection()
        if not selected:
            return
        item = self.cart_tree.item(selected[0])
        values = item['values']
        name, qty, price_str, subtotal_str = values
        
        # Parse price
        if isinstance(price_str, str):
            price = float(price_str.replace(',', ''))
        else:
            price = float(price_str)
        
        qty = int(qty)
        
        # Nếu số lượng = 1 thì xóa sản phẩm
        if qty <= 1:
            product_id = self._product_id_from_cart_iid(selected[0])
            self.cart_tree.delete(selected[0])
            self.cart_items.pop(product_id, None)
        else:
            # Nếu > 1 thì giảm đi 1
            new_qty = qty - 1
            subtotal = new_qty * price
            self.cart_tree.item(selected[0], values=(name, new_qty, f"{price:,.0f}", f"{subtotal:,.0f}"))
            product_id = self._product_id_from_cart_iid(selected[0])
            if product_id in self.cart_items:
                self.cart_items[product_id]['quantity'] = new_qty
        
        self.update_total()

    def update_total(self):
        total = 0
        for item in self.cart_tree.get_children():
            values = self.cart_tree.item(item)['values']
            subtotal_str = values[3]
            # Xử lý cả trường hợp string hoặc số
            if isinstance(subtotal_str, str):
                subtotal_str = subtotal_str.replace(',', '')
            total += float(subtotal_str)
        self.total_amount = total
        self.total_label.config(text=f"TỔNG TIỀN: {total:,.0f} ₫")
        
    def activate_scanner(self):
        from modules.styles import COLORS
        self.scanning_active = True
        self.scan_status.config(text="⚫ Sẵn sàng quét", fg=COLORS['success'])
        self.barcode_entry.config(bg=COLORS['success_light'])
        # Clear search khi activate scanner
        self.search_var.set("")
        self.barcode_entry.focus_set()

    def _on_barcode_focus_out(self, event):
        # Only steal focus back when scanning is active and no modal dialogs are grabbing input
        # Also check if search entry is focused - if so, don't steal focus
        try:
            current_grab = self.parent.grab_current()
            focused_widget = self.parent.focus_get()
        except Exception:
            current_grab = None
            focused_widget = None
        
        # Don't steal focus back if search entry or any other widget is focused
        if focused_widget == self.search_entry:
            return
        
        if self.scanning_active and current_grab is None:
            self.barcode_entry.focus_set()

    def on_barcode_scan(self, event):
        from modules.styles import COLORS
        if not self.scanning_active:
            return
        barcode = self.barcode_entry.get().strip()
        self.barcode_entry.delete(0, tk.END)
        # Đảm bảo entry luôn focus lại để quét liên tục
        self.parent.after(10, lambda: self.barcode_entry.focus_set())
        self.barcode_entry.config(bg=COLORS['info_light'])
        self.parent.after(200, lambda: self.barcode_entry.config(bg=COLORS['success_light']))
        if not barcode:
            return
        product = self.product_service.get_product_by_barcode(barcode)
        if not product:
            messagebox.showwarning("Không tìm thấy", "Không tìm thấy sản phẩm với mã vạch này!")
            return
        product_id, name, price, stock = product
        self._add_product_to_cart(product_id, name, price, stock)

    def clear_cart(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa giỏ hàng?"):
            for item in self.cart_tree.get_children():
                self.cart_tree.delete(item)
            self.cart.clear()
            self.cart_items.clear()
            self.update_total()
            self._set_action_status("Đã xóa giỏ hàng", 'info')

    def checkout(self):
        from modules.ui_checkout import CheckoutWindow
        if not self.cart_tree.get_children():
            messagebox.showwarning("Giỏ hàng trống", "Vui lòng thêm sản phẩm.")
            return
        CheckoutWindow(self)
