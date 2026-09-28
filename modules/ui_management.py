# modules/ui_management.py
import tkinter as tk
from tkinter import ttk, messagebox

from modules.app_logger import get_logger
from modules.services.product_service import (
    DuplicateBarcodeError,
    ProductService,
    ProductValidationError,
)
from modules.services.inventory_service import InventoryService


logger = get_logger(__name__)

class ManagementPanel:
    def __init__(self, parent, db, colors):
        self.parent = parent
        self.db = db
        self.colors = colors
        self.product_service = ProductService(self.db.conn)
        self.inventory_service = InventoryService(self.db.conn)
        # Biến tìm kiếm dùng chung cho table sản phẩm
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_products)
        self.category_var = tk.StringVar(value='Tất cả')
        self.category_var.trace('w', self.on_category_change)
        self.stock_filter = tk.StringVar(value='Tất cả tồn kho')
        self.create_widgets()

    def create_widgets(self):
        from modules.styles import COLORS, FONT, LAYOUT, button_style, card_style, entry_style, configure_treeview_style, enable_treeview_sorting
        self.parent.rowconfigure(1, weight=1)
        self.parent.columnconfigure(0, weight=1)
        self.parent.configure(bg=COLORS['background'])
        self.summary_label = tk.Label(self.parent, text='Sản phẩm & tồn kho',
            font=FONT['subtitle'], bg=COLORS['background'], fg=COLORS['text_primary'], anchor='w')
        self.summary_label.grid(row=0, column=0, columnspan=2, sticky='ew', padx=18, pady=16)
        
        # === FORM SECTION (COMPACT) ===
        form_frame = tk.Frame(self.parent, **card_style(compact=True))
        form_frame.grid(row=1, column=1, sticky='ns', padx=(0, LAYOUT['page_padx']), pady=(0, LAYOUT['page_pady']))
        
        # Form title
        self.form_title = tk.Label(
            form_frame,
            text="Thông tin sản phẩm",
            font=FONT['subtitle'],
            fg=COLORS['primary'],
            bg=COLORS['surface'],
            anchor='w'
        )
        self.form_title.grid(row=0, column=0, columnspan=4, sticky='w', padx=0, pady=(0, 8))

        # Create entry widgets
        self.product_name = tk.Entry(form_frame, width=LAYOUT['field_width'], **entry_style())
        self.product_barcode = tk.Entry(form_frame, width=LAYOUT['field_width'], **entry_style())
        self.product_price = tk.Entry(form_frame, width=LAYOUT['field_width'], **entry_style())
        self.product_stock = tk.Entry(form_frame, width=LAYOUT['field_width'], **entry_style())
        self.product_category = tk.Entry(form_frame, width=LAYOUT['field_width'], **entry_style())

        # Input fields in 2-column grid (compact)
        labels_config = [
            ('Tên sản phẩm', 0, 0, self.product_name),
            ('Mã vạch', 2, 0, self.product_barcode),
            ('Giá bán (đ)', 4, 0, self.product_price),
            ('Tồn kho', 6, 0, self.product_stock),
            ('Danh mục', 8, 0, self.product_category),
        ]
        
        for label_text, row, col, entry_widget in labels_config:
            # Label
            tk.Label(
                form_frame, 
                text=label_text, 
                bg=COLORS['surface'], 
                font=FONT['label'],
                fg=COLORS['text_primary']
            ).grid(row=row+1, column=0, columnspan=4, sticky='w', pady=(10, 4))
            # Entry
            entry_widget.grid(row=row+2, column=0, columnspan=4, sticky='ew', pady=3, ipady=4)

        # Configure column weights for input fields
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

        # Button frame - compact horizontal layout
        btn_frame = tk.Frame(form_frame, bg=COLORS['surface'])
        btn_frame.grid(row=11, column=0, columnspan=4, pady=(16, 0), sticky='ew')
        for col in range(3):
            btn_frame.columnconfigure(col, weight=1, uniform='management_buttons')
        
        tk.Button(btn_frame, text="➕ Thêm", command=self.add_product,
                 **button_style('primary', compact=True)).grid(row=0, column=0, sticky='ew', padx=(0, 3))
        
        tk.Button(btn_frame, text="✏️ Sửa", command=self.update_product,
                 **button_style('warning', compact=True)).grid(row=0, column=1, sticky='ew', padx=3)
        
        tk.Button(btn_frame, text="🗑️ Xóa", command=self.delete_product,
                 **button_style('danger', compact=True)).grid(row=0, column=2, sticky='ew', padx=(3, 0))

        tk.Button(btn_frame, text="📦 Nhập kho", command=self.import_stock,
                 **button_style('success', compact=True)).grid(row=1, column=0, sticky='ew', padx=(0, 3), pady=(5, 0))

        tk.Button(btn_frame, text="📋 Lịch sử kho", command=self.show_inventory_history,
                 **button_style('secondary', compact=True)).grid(row=1, column=1, sticky='ew', padx=3, pady=(5, 0))
        
        tk.Button(btn_frame, text="🔄 Làm mới", command=self.clear_product_form,
                 **button_style('secondary', compact=True)).grid(row=1, column=2, sticky='ew', padx=(3, 0), pady=(5, 0))

        # === TABLE SECTION ===
        table_frame = tk.Frame(self.parent, **card_style())
        table_frame.grid(row=1, column=0, sticky='nsew', padx=LAYOUT['page_padx'], pady=(0, LAYOUT['page_pady']))
        table_frame.rowconfigure(2, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        tk.Label(
            table_frame,
            text="Danh sách sản phẩm",
            font=FONT['subtitle'],
            fg=COLORS['primary'],
            bg=COLORS['surface'],
            anchor='w'
        ).grid(row=0, column=0, sticky='w', padx=0, pady=(0, LAYOUT['gap']))

        # Search and filter bar
        search_frame = tk.Frame(table_frame, bg=COLORS['surface'])
        search_frame.grid(row=1, column=0, sticky='ew', padx=0, pady=(0, LAYOUT['gap']))
        search_frame.columnconfigure(1, weight=3)
        search_frame.columnconfigure(3, weight=1)
        
        # Search field
        tk.Label(
            search_frame,
            text="🔍 Tìm sản phẩm:",
            font=FONT['label'],
            fg=COLORS['text_primary'],
            bg=COLORS['surface']
        ).grid(row=0, column=0, sticky='w', padx=(0, 8))
        tk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=16,
            **entry_style('search')
        ).grid(row=0, column=1, sticky='ew', padx=(0, 12))
        
        # Category filter
        tk.Label(
            search_frame,
            text="📂 Danh mục:",
            font=FONT['label'],
            fg=COLORS['text_primary'],
            bg=COLORS['surface']
        ).grid(row=0, column=2, sticky='w', padx=(0, 8))
        
        self.category_combobox = ttk.Combobox(
            search_frame,
            textvariable=self.category_var,
            values=['Tất cả'],
            state='readonly',
            width=12,
            font=FONT['input']
        )
        self.category_combobox.grid(row=0, column=3, sticky='ew')
        stock_combo = ttk.Combobox(search_frame, textvariable=self.stock_filter,
            values=['Tất cả tồn kho', 'Còn hàng', 'Sắp hết (≤ 10)', 'Hết hàng'],
            state='readonly', width=18, font=FONT['input'])
        stock_combo.grid(row=1, column=1, sticky='w', pady=(10, 0))
        stock_combo.bind('<<ComboboxSelected>>', lambda event: self.load_products())
        tk.Button(search_frame, text='Bỏ lọc', command=self.reset_product_filters,
            **button_style('secondary', compact=True)).grid(row=1, column=3, sticky='e', pady=(10, 0))
        self.load_categories()

        # Products table
        configure_treeview_style('Management.Treeview', 'management')

        columns = ('ID', 'Tên', 'Mã vạch', 'Giá', 'Số lượng', 'Danh mục')
        tree_frame = tk.Frame(table_frame, bg=COLORS['surface'])
        tree_frame.grid(row=2, column=0, sticky='nsew', padx=0, pady=0)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.products_tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show='headings', 
            style='Management.Treeview', 
            selectmode='browse',
            height=12
        )
        for col in columns:
            self.products_tree.heading(col, text=col)
            if col == 'Tên':
                self.products_tree.column(col, width=220, anchor='w', minwidth=120, stretch=True)
            elif col == 'ID':
                self.products_tree.column(col, width=55, anchor='center', minwidth=40, stretch=False)
            elif col in ('Giá', 'Số lượng'):
                self.products_tree.column(col, width=90, anchor='center', minwidth=70, stretch=False)
            else:
                self.products_tree.column(col, width=115, anchor='center', minwidth=80, stretch=True)
        # Scrollbar dọc
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=vsb.set)
        # Scrollbar ngang
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.products_tree.xview)
        self.products_tree.configure(xscrollcommand=hsb.set)
        self.products_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        enable_treeview_sorting(self.products_tree, numeric_columns={'ID', 'Giá', 'Số lượng'})
        self.products_tree.bind('<<TreeviewSelect>>', self.on_select_product)
        self.products_tree.tag_configure('low', foreground=COLORS['warning'])
        self.products_tree.tag_configure('empty', foreground=COLORS['danger'])
        self.load_products()

    def reset_product_filters(self):
        self.search_var.set('')
        self.category_var.set('Tất cả')
        self.stock_filter.set('Tất cả tồn kho')
        self.load_products()

    def load_products(self, search_term: str = None):
        """Nạp danh sách sản phẩm, có thể lọc theo tên (một phần) hoặc mã vạch, và danh mục."""
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)

        term = (search_term if search_term is not None else self.search_var.get()).strip().lower()
        category = self.category_var.get()
        products = self.product_service.search_products(term, category)
        stock_mode = self.stock_filter.get()
        products = [p for p in products if
            stock_mode == 'Tất cả tồn kho' or
            (stock_mode == 'Còn hàng' and p[4] > 0) or
            (stock_mode == 'Sắp hết (≤ 10)' and 0 < p[4] <= 10) or
            (stock_mode == 'Hết hàng' and p[4] == 0)]
        self.summary_label.config(text=f'Sản phẩm & tồn kho   ·   {len(products)} sản phẩm   ·   {sum(p[4] for p in products):,} đơn vị trong bộ lọc')
        for product in products:
            self.products_tree.insert('', 'end', values=product,
                tags=('empty' if product[4] == 0 else 'low' if product[4] <= 10 else '',))
        self.load_categories()

    def load_categories(self):
        """Nạp danh sách danh mục từ database."""
        categories = self.product_service.get_categories()
        values = ['Tất cả'] + categories
        self.category_combobox['values'] = values

    def on_category_change(self, *args):
        """Callback khi người dùng thay đổi danh mục."""
        self.load_products()

    def search_products(self, *args):
        """Callback trace để lọc danh sách khi người dùng gõ tìm kiếm."""
        self.load_products(self.search_var.get())

    def on_select_product(self, event):
        selected = self.products_tree.selection()
        if not selected:
            return
        item = self.products_tree.item(selected[0])['values']
        self.selected_product_id = item[0]
        self.form_title.config(text=f'Đang sửa sản phẩm #{item[0]}')
        self.product_name.delete(0, tk.END)
        self.product_name.insert(0, item[1])
        self.product_barcode.delete(0, tk.END)
        self.product_barcode.insert(0, item[2] if item[2] else '')
        self.product_price.delete(0, tk.END)
        self.product_price.insert(0, item[3])
        self.product_stock.delete(0, tk.END)
        self.product_stock.insert(0, item[4])
        self.product_category.delete(0, tk.END)
        self.product_category.insert(0, item[5] if item[5] else '')

    def _validate_product_form(self):
        try:
            data = self.product_service.validate_product_input(
                self.product_name.get(),
                self.product_barcode.get(),
                self.product_price.get(),
                self.product_stock.get(),
                self.product_category.get(),
            )
        except ProductValidationError as exc:
            messagebox.showerror("Lỗi", str(exc))
            return None

        return data['name'], data['barcode'], data['price'], data['stock'], data['category']

    def _warn_duplicate_name(self, name, exclude_id=None):
        if self.product_service.product_name_exists(name, exclude_id=exclude_id):
            messagebox.showwarning("Tên sản phẩm trùng", "Tên sản phẩm đã tồn tại. App vẫn tiếp tục lưu vì barcode/ID là định danh chính.")

    def add_product(self):
        product_data = self._validate_product_form()
        if not product_data:
            return
        name, barcode, price, stock, category = product_data
        self._warn_duplicate_name(name)
        try:
            self.product_service.create_product(name, barcode, price, stock, category)
            messagebox.showinfo("Thành công", "Đã thêm sản phẩm mới!")
            self.clear_product_form()
            self.load_products()
        except DuplicateBarcodeError:
            logger.exception("Add product failed because barcode already exists: %s", barcode)
            messagebox.showerror("Lỗi", "Mã vạch đã tồn tại")
        except Exception:
            logger.exception("Add product failed")
            messagebox.showerror("Lỗi", "Không thể thêm sản phẩm. Vui lòng kiểm tra log.")

    def update_product(self):
        if not hasattr(self, 'selected_product_id'):
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn sản phẩm cần sửa!")
            return
        product_data = self._validate_product_form()
        if not product_data:
            return
        name, barcode, price, stock, category = product_data
        self._warn_duplicate_name(name, exclude_id=self.selected_product_id)
        try:
            self.product_service.update_product(self.selected_product_id, name, barcode, price, stock, category)
            messagebox.showinfo("Thành công", "Đã cập nhật sản phẩm!")
            self.clear_product_form()
            self.load_products()
        except DuplicateBarcodeError:
            logger.exception("Update product failed because barcode already exists: %s", barcode)
            messagebox.showerror("Lỗi", "Mã vạch đã tồn tại")
        except Exception:
            logger.exception("Update product failed")
            messagebox.showerror("Lỗi", "Không thể cập nhật sản phẩm. Vui lòng kiểm tra log.")

    def delete_product(self):
        if not hasattr(self, 'selected_product_id'):
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn sản phẩm cần xóa!")
            return
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa sản phẩm này?"):
            try:
                self.product_service.delete_product(self.selected_product_id)
                messagebox.showinfo("Thành công", "Đã xóa sản phẩm!")
                self.clear_product_form()
                self.load_products()
            except Exception:
                logger.exception("Delete product failed: product_id=%s", self.selected_product_id)
                messagebox.showerror("Lỗi", "Không thể xóa sản phẩm. Vui lòng kiểm tra log.")

    def _get_selected_product_label(self):
        selected = self.products_tree.selection()
        if selected:
            values = self.products_tree.item(selected[0])['values']
            if len(values) > 1:
                return values[1]
        return self.product_name.get().strip() or f"ID {self.selected_product_id}"

    def import_stock(self):
        if not hasattr(self, 'selected_product_id'):
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn sản phẩm cần nhập kho!")
            return

        from modules.styles import COLORS, FONT, button_style, entry_style

        product_name = self._get_selected_product_label()
        import_window = tk.Toplevel(self.parent)
        import_window.title("Nhập kho")
        import_window.geometry("420x220")
        import_window.configure(bg=COLORS['surface'])
        import_window.transient(self.parent)
        import_window.grab_set()

        quantity_var = tk.StringVar()
        note_var = tk.StringVar(value="Nhập kho thủ công")

        tk.Label(
            import_window,
            text=f"Nhập kho: {product_name}",
            font=FONT['subtitle'],
            bg=COLORS['surface'],
            fg=COLORS['primary'],
            anchor='w',
        ).pack(fill=tk.X, padx=16, pady=(14, 10))

        form_frame = tk.Frame(import_window, bg=COLORS['surface'])
        form_frame.pack(fill=tk.X, padx=16)
        form_frame.columnconfigure(1, weight=1)

        tk.Label(form_frame, text="Số lượng nhập:", font=FONT['label'], bg=COLORS['surface']).grid(
            row=0, column=0, sticky='e', padx=(0, 8), pady=6
        )
        quantity_entry = tk.Entry(form_frame, textvariable=quantity_var, **entry_style())
        quantity_entry.grid(row=0, column=1, sticky='ew', pady=6)

        tk.Label(form_frame, text="Ghi chú:", font=FONT['label'], bg=COLORS['surface']).grid(
            row=1, column=0, sticky='e', padx=(0, 8), pady=6
        )
        tk.Entry(form_frame, textvariable=note_var, **entry_style()).grid(row=1, column=1, sticky='ew', pady=6)

        def submit_import():
            try:
                stock_after = self.inventory_service.increase_stock(
                    self.selected_product_id,
                    quantity_var.get(),
                    note=note_var.get().strip() or "Nhập kho thủ công",
                )
                messagebox.showinfo("Thành công", f"Đã nhập kho. Tồn kho mới: {stock_after}")
                import_window.destroy()
                self.clear_product_form()
                self.load_products()
            except Exception as exc:
                logger.exception("Import stock failed: product_id=%s", self.selected_product_id)
                messagebox.showerror("Lỗi", str(exc))

        btn_frame = tk.Frame(import_window, bg=COLORS['surface'])
        btn_frame.pack(fill=tk.X, padx=16, pady=(12, 0))
        tk.Button(btn_frame, text="Xác nhận", command=submit_import, **button_style('success', compact=True)).pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        tk.Button(btn_frame, text="Hủy", command=import_window.destroy, **button_style('secondary', compact=True)).pack(
            side=tk.RIGHT
        )

        quantity_entry.focus_set()

    def show_inventory_history(self):
        from modules.styles import COLORS, FONT, button_style, configure_treeview_style, enable_treeview_sorting

        product_id = getattr(self, 'selected_product_id', None)
        product_name = self._get_selected_product_label() if product_id is not None else None
        movements = self.inventory_service.get_movements(product_id=product_id, limit=100)

        history_window = tk.Toplevel(self.parent)
        history_window.title("Lịch sử tồn kho")
        history_window.geometry("920x420")
        history_window.configure(bg=COLORS['surface'])
        history_window.transient(self.parent)

        title = "Lịch sử tồn kho"
        if product_name:
            title += f" - {product_name}"

        tk.Label(
            history_window,
            text=title,
            font=FONT['subtitle'],
            bg=COLORS['surface'],
            fg=COLORS['primary'],
            anchor='w',
        ).pack(fill=tk.X, padx=12, pady=(12, 8))

        configure_treeview_style('InventoryHistory.Treeview', 'management')
        columns = ('Thời gian', 'ID SP', 'Sản phẩm', 'Loại', 'Thay đổi', 'Trước', 'Sau', 'Ghi chú')
        tree_frame = tk.Frame(history_window, bg=COLORS['surface'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        history_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            style='InventoryHistory.Treeview',
            height=10,
        )
        widths = {
            'Thời gian': 145,
            'ID SP': 55,
            'Sản phẩm': 180,
            'Loại': 100,
            'Thay đổi': 80,
            'Trước': 70,
            'Sau': 70,
            'Ghi chú': 220,
        }
        for col in columns:
            history_tree.heading(col, text=col)
            history_tree.column(col, width=widths[col], minwidth=50, anchor='center' if col != 'Sản phẩm' and col != 'Ghi chú' else 'w')

        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=history_tree.yview)
        history_tree.configure(yscrollcommand=vsb.set)
        history_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        enable_treeview_sorting(
            history_tree,
            numeric_columns={'ID SP', 'Thay đổi', 'Trước', 'Sau'},
            date_columns={'Thời gian'},
        )

        movement_labels = {
            'SALE': 'Bán hàng',
            'IMPORT': 'Nhập kho',
            'ADJUSTMENT': 'Điều chỉnh',
        }
        for movement in movements:
            quantity_change = int(movement['quantity_change'])
            quantity_text = f"+{quantity_change}" if quantity_change > 0 else str(quantity_change)
            history_tree.insert(
                '',
                'end',
                values=(
                    movement['created_at'],
                    movement['product_id'],
                    movement['product_name'],
                    movement_labels.get(movement['movement_type'], movement['movement_type']),
                    quantity_text,
                    movement['stock_before'],
                    movement['stock_after'],
                    movement['note'],
                ),
            )

        footer = tk.Frame(history_window, bg=COLORS['surface'])
        footer.pack(fill=tk.X, padx=12, pady=(0, 12))
        tk.Button(footer, text="Đóng", command=history_window.destroy, **button_style('secondary', compact=True)).pack(
            side=tk.RIGHT
        )

    def clear_product_form(self):
        self.form_title.config(text='Thêm sản phẩm mới')
        self.products_tree.selection_remove(self.products_tree.selection())
        self.product_name.delete(0, tk.END)
        self.product_barcode.delete(0, tk.END)
        self.product_price.delete(0, tk.END)
        self.product_stock.delete(0, tk.END)
        self.product_category.delete(0, tk.END)
        if hasattr(self, 'selected_product_id'):
            del self.selected_product_id
