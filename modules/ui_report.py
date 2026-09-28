# modules/ui_report.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from modules.utils import format_currency
from modules.report_exporter import ReportDataService, RevenueReportExporter, TabularReportExporter
from modules.app_logger import get_logger
from datetime import datetime
from pathlib import Path


logger = get_logger(__name__)


class ReportPanel:
    def __init__(self, parent, db, colors):
        self.parent = parent
        self.db = db
        self.colors = colors
        self.selected_period = tk.StringVar(value='day')
        self.selected_year = tk.IntVar(value=datetime.now().year)
        self.selected_month = tk.IntVar(value=datetime.now().month)
        self.selected_day = tk.IntVar(value=datetime.now().day)
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.payment_filter_var = tk.StringVar(value='Tất cả')
        self.product_filter_var = tk.StringVar(value='Tất cả')
        self.category_filter_var = tk.StringVar(value='Tất cả')
        self.product_filter_map = {'Tất cả': None}
        self.report_service = ReportDataService(self.db.conn)
        self.report_exporter = RevenueReportExporter()
        self.table_exporter = TabularReportExporter()
        self.create_widgets()
        self.load_date_options()
        self.load_filter_options()
        self.refresh_report()

    def create_widgets(self):
        from modules.styles import (
            COLORS,
            FONT,
            LAYOUT,
            button_style,
            card_style,
            configure_treeview_style,
            create_scrollable_frame,
            enable_treeview_sorting,
        )
        self.parent.rowconfigure(1, weight=1)
        self.parent.columnconfigure(0, weight=1)
        
        # === TOP BAR ===
        top_bar = tk.Frame(self.parent, bg=COLORS['background'], padx=18, pady=14)
        top_bar.grid(row=0, column=0, sticky='ew')
        
        left_section = tk.Frame(top_bar, bg=COLORS['background'])
        left_section.pack(side=tk.LEFT)
        
        tk.Label(left_section, text="Thống kê kinh doanh",
                font=FONT['title'], bg=COLORS['background'], fg=COLORS['text_primary']).pack(side=tk.LEFT)

        tk.Button(
            top_bar,
            text="📄 Xuất PDF",
            command=self.export_pdf,
            **button_style('success', compact=True)
        ).pack(side=tk.RIGHT)
        tk.Button(
            top_bar,
            text="📊 Excel",
            command=self.export_excel,
            **button_style('warning', compact=True)
        ).pack(side=tk.RIGHT, padx=(0, 6))
        tk.Button(
            top_bar,
            text="CSV",
            command=self.export_csv,
            **button_style('secondary', compact=True)
        ).pack(side=tk.RIGHT, padx=(0, 6))
        self.status_label = tk.Label(
            top_bar,
            text="",
            font=FONT['body_small'],
            bg=COLORS['background'],
            fg=COLORS['text_secondary']
        )
        self.status_label.pack(side=tk.RIGHT, padx=(0, 12))
        
        body_shell, body = create_scrollable_frame(self.parent, bg=COLORS['background'])
        body_shell.grid(row=1, column=0, sticky='nsew')
        body.columnconfigure(0, weight=1)

        # === DATE SELECTOR ===
        date_selector_frame = tk.Frame(body, **card_style(compact=True))
        date_selector_frame.grid(row=0, column=0, sticky='ew', padx=LAYOUT['page_padx'], pady=(LAYOUT['page_pady'], LAYOUT['gap']))
        date_selector_frame.columnconfigure(0, weight=1)
        
        tk.Label(date_selector_frame, text="📅 CHỌN XEM DOANH THU THEO", 
                font=FONT['subtitle'], fg=COLORS['primary'], bg=COLORS['surface']).grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['gap']))
        
        # View mode selection (Day / Month / Year)
        mode_frame = tk.Frame(date_selector_frame, bg=COLORS['surface'])
        mode_frame.grid(row=1, column=0, sticky='ew', pady=(0, LAYOUT['gap']))
        mode_frame.columnconfigure(4, weight=1)
        
        tk.Label(mode_frame, text="Chế độ xem:", font=FONT['label'], 
                fg=COLORS['text_primary'], bg=COLORS['surface']).grid(row=0, column=0, sticky='w', padx=(0, 8))
        
        self.period_buttons = {}
        for period_value, period_label, emoji in [('day', 'NGÀY', '📆'), 
                                                   ('month', 'THÁNG', '📅'), 
                                                   ('year', 'NĂM', '📊')]:
            btn = tk.Button(
                mode_frame,
                text=f"{emoji} {period_label}",
                command=lambda p=period_value: self.set_period_mode(p),
                **button_style('primary', compact=True, bg=COLORS['primary_dark'], activebackground=COLORS['success'])
            )
            btn.grid(row=0, column=len(self.period_buttons) + 1, sticky='w', padx=(0, 5))
            self.period_buttons[period_value] = btn
        
        self.update_period_buttons()
        
        # Date input fields - Dynamic based on mode
        self.input_frame = tk.Frame(date_selector_frame, bg=COLORS['surface'])
        self.input_frame.grid(row=2, column=0, sticky='ew')
        self.input_frame.columnconfigure(5, weight=1)
        self.create_date_inputs()

        self.create_advanced_filters(body)
        self.sections = ttk.Notebook(body, style='Modern.TNotebook')
        self.sections.grid(row=2, column=0, sticky='nsew', padx=LAYOUT['page_padx'], pady=(0, 14))
        overview = tk.Frame(self.sections, bg=COLORS['background'])
        overview.columnconfigure(0, weight=1)
        history_page = tk.Frame(self.sections, bg=COLORS['background'])
        history_page.columnconfigure(0, weight=1)
        history_page.rowconfigure(0, weight=1)
        self.sections.add(overview, text='  Tổng quan  ')
        self.sections.add(history_page, text='  Lịch sử giao dịch  ')
        
        # === MAIN CONTENT ===
        main_container = tk.Frame(overview, bg=COLORS['background'])
        main_container.grid(row=2, column=0, sticky='ew', padx=LAYOUT['page_padx'], pady=(0, LAYOUT['gap']))
        main_container.columnconfigure(0, weight=1)
        
        # Stat cards - compact 3 columns x 2 rows
        stats_frame = tk.Frame(main_container, bg=COLORS['background'])
        stats_frame.grid(row=0, column=0, sticky='ew', pady=(0, LAYOUT['gap']))
        for col in range(3):
            stats_frame.columnconfigure(col, weight=1, uniform='report_stats')
        
        self.subtotal_card = self._create_stat_card(stats_frame, "🧾 TRƯỚC GIẢM", "0 ₫", 0, 0, COLORS['primary'])
        self.discount_card = self._create_stat_card(stats_frame, "🏷️ TỔNG GIẢM", "0 ₫", 0, 1, COLORS['danger'])
        self.revenue_card = self._create_stat_card(stats_frame, "DOANH THU SAU HOÀN", "0 ₫", 0, 2, COLORS['success'])
        self.transaction_card = self._create_stat_card(stats_frame, "CHỨNG TỪ BÁN + HOÀN", "0", 1, 0, COLORS['info'])
        self.avg_card = self._create_stat_card(stats_frame, "TRUNG BÌNH / ĐƠN BÁN", "0 ₫", 1, 1, COLORS['warning'])
        self.products_sold_card = self._create_stat_card(stats_frame, "SẢN PHẨM BÁN RÒNG", "0", 1, 2, COLORS['primary'])
        self.refund_hint = tk.Label(stats_frame, text='', font=FONT['body_small'], bg=COLORS['background'], fg=COLORS['text_secondary'])
        self.refund_hint.grid(row=2,column=0,columnspan=3,sticky='w',padx=4,pady=8)
        
        configure_treeview_style('Report.Treeview', 'report')
        chart_frame = tk.Frame(main_container, **card_style(compact=True))
        chart_frame.grid(row=1, column=0, sticky='ew', pady=(0, LAYOUT['gap']))
        tk.Label(chart_frame, text='Doanh thu sau giảm · 14 ngày có giao dịch gần nhất trong bộ lọc',
            font=FONT['label'], bg=COLORS['surface'], fg=COLORS['text_primary']).pack(anchor='w')
        self.trend_canvas = tk.Canvas(chart_frame, height=160, bg=COLORS['surface'], highlightthickness=0)
        self.trend_canvas.pack(fill='x')
        self.trend_rows = []
        self.trend_canvas.bind('<Configure>', self.draw_trend)

        # Content: payment breakdown + product rankings + low stock
        content_frame = tk.Frame(main_container, bg=COLORS['background'])
        content_frame.grid(row=2, column=0, sticky='ew')
        content_frame.columnconfigure(0, weight=1, uniform='report_cols')
        content_frame.columnconfigure(1, weight=1, uniform='report_cols')
        content_frame.rowconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)
        
        top_qty_frame = tk.Frame(content_frame, **card_style(compact=True))
        top_qty_frame.grid(row=0, column=0, sticky='nsew', padx=(0, LAYOUT['small_gap']), pady=(0, LAYOUT['small_gap']))
        top_qty_frame.rowconfigure(1, weight=1)
        top_qty_frame.columnconfigure(0, weight=1)
        
        tk.Label(top_qty_frame, text="🏆 TOP 5 SẢN PHẨM BÁN CHẠY", 
                font=FONT['label'], fg=COLORS['primary'], bg=COLORS['surface']).grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['small_gap']))
        
        self.top_products_text = scrolledtext.ScrolledText(
            top_qty_frame, width=1, height=6, font=FONT['body_small'], 
            bg=COLORS['background'], fg=COLORS['text_primary'], bd=0, relief='flat'
        )
        self.top_products_text.grid(row=1, column=0, sticky='nsew')

        top_revenue_frame = tk.Frame(content_frame, **card_style(compact=True))
        top_revenue_frame.grid(row=0, column=1, sticky='nsew', padx=(LAYOUT['small_gap'], 0), pady=(0, LAYOUT['small_gap']))
        top_revenue_frame.rowconfigure(1, weight=1)
        top_revenue_frame.columnconfigure(0, weight=1)

        tk.Label(top_revenue_frame, text="💎 TOP 5 THEO DOANH THU",
                font=FONT['label'], fg=COLORS['success'], bg=COLORS['surface']).grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['small_gap']))

        self.top_revenue_text = scrolledtext.ScrolledText(
            top_revenue_frame, width=1, height=6, font=FONT['body_small'],
            bg=COLORS['background'], fg=COLORS['text_primary'], bd=0, relief='flat'
        )
        self.top_revenue_text.grid(row=1, column=0, sticky='nsew')
        
        payment_frame = tk.Frame(content_frame, **card_style(compact=True))
        payment_frame.grid(row=1, column=0, sticky='nsew', padx=(0, LAYOUT['small_gap']), pady=(LAYOUT['small_gap'], 0))
        payment_frame.rowconfigure(1, weight=1)
        payment_frame.columnconfigure(0, weight=1)

        tk.Label(payment_frame, text="💳 DOANH THU THEO PTTT",
                font=FONT['label'], fg=COLORS['info'], bg=COLORS['surface']).grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['small_gap']))

        payment_cols = ('Phương thức', 'Số GD', 'Doanh thu')
        payment_tree_frame = tk.Frame(payment_frame, bg=COLORS['surface'])
        payment_tree_frame.grid(row=1, column=0, sticky='nsew')
        payment_tree_frame.rowconfigure(0, weight=1)
        payment_tree_frame.columnconfigure(0, weight=1)
        self.payment_tree = ttk.Treeview(
            payment_tree_frame,
            columns=payment_cols,
            show='headings',
            style='Report.Treeview',
            height=5
        )
        for col in payment_cols:
            self.payment_tree.heading(col, text=col)
            if col == 'Phương thức':
                self.payment_tree.column(col, width=130, minwidth=90, stretch=True)
            elif col == 'Số GD':
                self.payment_tree.column(col, width=65, minwidth=55, anchor='center', stretch=False)
            else:
                self.payment_tree.column(col, width=120, minwidth=85, anchor='e', stretch=True)

        payment_vsb = ttk.Scrollbar(payment_tree_frame, orient='vertical', command=self.payment_tree.yview)
        self.payment_tree.configure(yscrollcommand=payment_vsb.set)
        self.payment_tree.grid(row=0, column=0, sticky='nsew')
        payment_vsb.grid(row=0, column=1, sticky='ns')
        enable_treeview_sorting(self.payment_tree, numeric_columns={'Số GD', 'Doanh thu'})

        low_stock_frame = tk.Frame(content_frame, **card_style(compact=True))
        low_stock_frame.grid(row=1, column=1, sticky='nsew', padx=(LAYOUT['small_gap'], 0), pady=(LAYOUT['small_gap'], 0))
        low_stock_frame.rowconfigure(1, weight=1)
        low_stock_frame.columnconfigure(0, weight=1)
        
        tk.Label(low_stock_frame, text="⚠️ CẦN NHẬP THÊM", 
                font=FONT['label'], fg=COLORS['danger'], bg=COLORS['surface']).grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['small_gap']))
        
        self.low_stock_text = scrolledtext.ScrolledText(
            low_stock_frame, width=1, height=6, font=FONT['body_small'], 
            bg=COLORS['background'], fg=COLORS['text_primary'], bd=0, relief='flat'
        )
        self.low_stock_text.grid(row=1, column=0, sticky='nsew')
        
        # Bottom: Transaction history
        history_frame = tk.Frame(history_page, **card_style())
        history_frame.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)
        history_frame.rowconfigure(1, weight=1)
        history_frame.columnconfigure(0, weight=1)
        
        tk.Label(history_frame, text="50 giao dịch gần nhất trong kỳ · Xuất báo cáo để xem toàn bộ", 
                font=FONT['label'], fg=COLORS['primary'], bg=COLORS['surface']).grid(row=0, column=0, sticky='w', pady=(0, LAYOUT['gap']))

        history_cols = ('ID', 'Ngày giờ', 'Trước giảm', 'Giảm', 'Thanh toán', 'PT Thanh toán')
        tree_frame = tk.Frame(history_frame, bg=COLORS['surface'])
        tree_frame.grid(row=1, column=0, sticky='nsew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=history_cols,
            show='headings',
            style='Report.Treeview',
            selectmode='browse',
            height=16
        )
        for col in history_cols:
            self.history_tree.heading(col, text=col)
            if col == 'Ngày giờ':
                self.history_tree.column(col, anchor='center', width=140, minwidth=100, stretch=True)
            elif col == 'ID':
                self.history_tree.column(col, anchor='center', width=60, minwidth=45, stretch=False)
            elif col == 'PT Thanh toán':
                self.history_tree.column(col, anchor='center', width=110, minwidth=80, stretch=True)
            else:
                self.history_tree.column(col, anchor='center', width=100, minwidth=80, stretch=True)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(xscrollcommand=hsb.set)
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        enable_treeview_sorting(
            self.history_tree,
            numeric_columns={'ID', 'Trước giảm', 'Giảm', 'Thanh toán'},
            date_columns={'Ngày giờ'},
        )

    def _set_status(self, message, is_error=False):
        from modules.styles import COLORS
        if hasattr(self, 'status_label'):
            self.status_label.config(
                text=message,
                fg=COLORS['danger_light'] if is_error else COLORS['surface'],
            )
            self.parent.after(6000, lambda: self.status_label.config(text=""))

    def create_advanced_filters(self, body):
        from modules.styles import COLORS, FONT, LAYOUT, button_style, card_style, entry_style

        filters_frame = tk.Frame(body, **card_style(compact=True))
        filters_frame.grid(row=1, column=0, sticky='ew', padx=LAYOUT['page_padx'], pady=(0, LAYOUT['gap']))
        for col in range(8):
            filters_frame.columnconfigure(col, weight=1 if col in (1, 3, 5, 7) else 0)

        tk.Label(
            filters_frame,
            text="🔎 BỘ LỌC NÂNG CAO",
            font=FONT['subtitle'],
            fg=COLORS['primary'],
            bg=COLORS['surface'],
            anchor='w'
        ).grid(row=0, column=0, columnspan=8, sticky='w', pady=(0, LAYOUT['small_gap']))

        tk.Label(filters_frame, text="Từ ngày:", font=FONT['label'], bg=COLORS['surface']).grid(
            row=1, column=0, sticky='e', padx=(0, 6), pady=3
        )
        tk.Entry(filters_frame, textvariable=self.start_date_var, width=12, **entry_style()).grid(
            row=1, column=1, sticky='ew', padx=(0, LAYOUT['gap']), pady=3
        )

        tk.Label(filters_frame, text="Đến ngày:", font=FONT['label'], bg=COLORS['surface']).grid(
            row=1, column=2, sticky='e', padx=(0, 6), pady=3
        )
        tk.Entry(filters_frame, textvariable=self.end_date_var, width=12, **entry_style()).grid(
            row=1, column=3, sticky='ew', padx=(0, LAYOUT['gap']), pady=3
        )

        tk.Label(filters_frame, text="PTTT:", font=FONT['label'], bg=COLORS['surface']).grid(
            row=1, column=4, sticky='e', padx=(0, 6), pady=3
        )
        self.payment_filter_combo = ttk.Combobox(
            filters_frame,
            textvariable=self.payment_filter_var,
            values=['Tất cả'],
            state='readonly',
            width=14,
            font=FONT['input'],
        )
        self.payment_filter_combo.grid(row=1, column=5, sticky='ew', padx=(0, LAYOUT['gap']), pady=3)
        self.payment_filter_combo.bind('<<ComboboxSelected>>', self.refresh_report)

        tk.Label(filters_frame, text="Sản phẩm:", font=FONT['label'], bg=COLORS['surface']).grid(
            row=2, column=0, sticky='e', padx=(0, 6), pady=3
        )
        self.product_filter_combo = ttk.Combobox(
            filters_frame,
            textvariable=self.product_filter_var,
            values=['Tất cả'],
            state='readonly',
            width=28,
            font=FONT['input'],
        )
        self.product_filter_combo.grid(row=2, column=1, columnspan=3, sticky='ew', padx=(0, LAYOUT['gap']), pady=3)
        self.product_filter_combo.bind('<<ComboboxSelected>>', self.refresh_report)

        tk.Label(filters_frame, text="Danh mục:", font=FONT['label'], bg=COLORS['surface']).grid(
            row=2, column=4, sticky='e', padx=(0, 6), pady=3
        )
        self.category_filter_combo = ttk.Combobox(
            filters_frame,
            textvariable=self.category_filter_var,
            values=['Tất cả'],
            state='readonly',
            width=18,
            font=FONT['input'],
        )
        self.category_filter_combo.grid(row=2, column=5, sticky='ew', padx=(0, LAYOUT['gap']), pady=3)
        self.category_filter_combo.bind('<<ComboboxSelected>>', self.refresh_report)

        tk.Button(
            filters_frame,
            text="Áp dụng",
            command=self.refresh_report,
            **button_style('primary', compact=True)
        ).grid(row=1, column=6, sticky='ew', padx=(0, LAYOUT['small_gap']), pady=3)
        tk.Button(
            filters_frame,
            text="Xóa lọc",
            command=self.reset_filters,
            **button_style('secondary', compact=True)
        ).grid(row=1, column=7, sticky='ew', pady=3)

    def load_filter_options(self):
        payment_values = ['Tất cả'] + self.report_service.get_payment_methods()
        if hasattr(self, 'payment_filter_combo'):
            self.payment_filter_combo['values'] = payment_values
            if self.payment_filter_var.get() not in payment_values:
                self.payment_filter_var.set('Tất cả')

        product_values = ['Tất cả']
        product_map = {'Tất cả': None}
        for product in self.report_service.get_product_filter_options():
            barcode_suffix = f" [{product['barcode']}]" if product['barcode'] else ''
            label = f"{product['id']} - {product['name']}{barcode_suffix}"
            product_values.append(label)
            product_map[label] = {'id': product['id'], 'name': product['name']}
        self.product_filter_map = product_map
        if hasattr(self, 'product_filter_combo'):
            self.product_filter_combo['values'] = product_values
            if self.product_filter_var.get() not in product_values:
                self.product_filter_var.set('Tất cả')

        category_values = ['Tất cả'] + self.report_service.get_category_filter_options()
        if hasattr(self, 'category_filter_combo'):
            self.category_filter_combo['values'] = category_values
            if self.category_filter_var.get() not in category_values:
                self.category_filter_var.set('Tất cả')

    def get_current_report_context(self):
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()

        if start_date or end_date:
            context = self.report_service.build_range_period(start_date or None, end_date or None)
        else:
            context = self.get_selected_period_context()

        product_info = self.product_filter_map.get(self.product_filter_var.get())
        product_id = product_info['id'] if product_info else None
        product_name = product_info['name'] if product_info else None

        return self.report_service.apply_filters(
            context,
            payment_method=self.payment_filter_var.get(),
            product_id=product_id,
            product_name=product_name,
            category=self.category_filter_var.get(),
        )

    def refresh_report(self, *_):
        try:
            self.load_filter_options()
            self.update_stats()
            self.load_transaction_history()
        except Exception as exc:
            logger.exception("Report refresh failed")
            messagebox.showerror("Lỗi báo cáo", str(exc))
            self._set_status("Lọc báo cáo lỗi", is_error=True)

    def reset_filters(self):
        self.start_date_var.set('')
        self.end_date_var.set('')
        self.payment_filter_var.set('Tất cả')
        self.product_filter_var.set('Tất cả')
        self.category_filter_var.set('Tất cả')
        self.refresh_report()

    def create_date_inputs(self):
        """Tạo input fields cho date selection dựa vào period mode"""
        from modules.styles import COLORS, FONT, LAYOUT
        
        # Clear existing inputs
        for widget in self.input_frame.winfo_children():
            widget.destroy()

        for col in range(7):
            self.input_frame.columnconfigure(col, weight=0)
        self.input_frame.columnconfigure(6, weight=1)

        def add_combo(label_text, variable, col, values=None):
            tk.Label(
                self.input_frame,
                text=label_text,
                font=FONT['label'],
                fg=COLORS['text_primary'],
                bg=COLORS['surface']
            ).grid(row=0, column=col, sticky='w', padx=(0, 6), pady=2)

            combo = ttk.Combobox(
                self.input_frame,
                textvariable=variable,
                state='readonly',
                width=8,
                font=FONT['input'],
                values=values or []
            )
            combo.grid(row=0, column=col + 1, sticky='w', padx=(0, LAYOUT['gap']), pady=2)
            combo.bind('<<ComboboxSelected>>', lambda e: self.on_date_change())
            return combo
        
        period = self.selected_period.get()
        
        if period == 'year':
            # Year selector only
            self.year_combo = add_combo("Năm:", self.selected_year, 0)
            
        elif period == 'month':
            # Month + Year selector
            self.month_combo = add_combo("Tháng:", self.selected_month, 0, [f'{i:02d}' for i in range(1, 13)])
            self.year_combo = add_combo("Năm:", self.selected_year, 2)
            
        else:  # day
            # Day + Month + Year selector
            self.day_combo = add_combo("Ngày:", self.selected_day, 0, [f'{i:02d}' for i in range(1, 32)])
            self.month_combo = add_combo("Tháng:", self.selected_month, 2, [f'{i:02d}' for i in range(1, 13)])
            self.year_combo = add_combo("Năm:", self.selected_year, 4)

    def load_date_options(self):
        """Load available years/months/days from database"""
        # Load available years
        self.db.cursor.execute('''
            SELECT DISTINCT strftime('%Y', transaction_date) as year 
            FROM transactions 
            ORDER BY year DESC
        ''')
        years = [int(row[0]) for row in self.db.cursor.fetchall()]
        if not years:
            years = [datetime.now().year]
        
        # Ensure year combobox exists and has values
        if hasattr(self, 'year_combo'):
            self.year_combo['values'] = years

    def on_date_change(self):
        """Callback when date selection changes"""
        # Update available years in case it's needed
        self.load_date_options()
        self.refresh_report()

    def _create_stat_card(self, parent, title, value, row, col, color):
        """Tạo stat card nhỏ gọn"""
        from modules.styles import COLORS, FONT, card_style
        
        card = tk.Frame(parent, **card_style(compact=True))
        card.grid(row=row, column=col, sticky='nsew', padx=3, pady=5)
        
        title_label = tk.Label(card, text=title, font=FONT['body'], 
                              fg=color, bg=COLORS['surface'], anchor='w')
        title_label.pack(anchor='w', pady=(0, 8))
        
        value_label = tk.Label(card, text=value, font=FONT['subtitle'], 
                              fg=color, bg=COLORS['surface'], anchor='w')
        value_label.pack(anchor='w')
        
        return value_label

    def set_period_mode(self, period):
        """Set period mode (day/month/year) và update inputs"""
        self.selected_period.set(period)
        self.create_date_inputs()
        self.load_date_options()
        self.update_period_buttons()
        self.refresh_report()

    def update_period_buttons(self):
        """Cập nhật style của period buttons"""
        from modules.styles import COLORS
        
        current = self.selected_period.get()
        for period, btn in self.period_buttons.items():
            if period == current:
                # Active button
                btn.config(bg=COLORS['success'], relief='solid', borderwidth=1)
            else:
                # Inactive button
                btn.config(bg=COLORS['primary_dark'], relief='solid', borderwidth=1)

    def get_selected_period_context(self):
        """Lấy kỳ báo cáo hiện tại đã validate ngày/tháng/năm."""
        return self.report_service.build_period(
            self.selected_period.get(),
            self.selected_year.get(),
            self.selected_month.get(),
            self.selected_day.get(),
        )

    def get_period_filter(self, table_alias=None):
        """Helper tương thích: trả về filter SQL đã parameterize cho kỳ hiện tại."""
        context = self.get_selected_period_context()
        where_clause, params = self.report_service.get_period_filter(context, table_alias=table_alias)
        return where_clause, params, context.label

    def update_stats(self):
        """Cập nhật stats dựa vào period chọn"""
        context = self.get_current_report_context()
        summary = self.report_service.get_summary(context)
        self.refund_hint.config(text=f"{summary['sale_count']} đơn bán · {summary['refund_count']} phiếu hoàn · Tiền hoàn trong kỳ: {format_currency(summary['refunded_amount'])}")
        self.trend_rows = self.report_service.get_daily_revenue(context)
        self.draw_trend()

        self.subtotal_card.config(text=format_currency(summary['subtotal_revenue']))
        self.discount_card.config(text=format_currency(summary['total_discount']))
        self.revenue_card.config(text=format_currency(summary['total_revenue']))
        self.transaction_card.config(text=str(summary['transaction_count']))
        self.avg_card.config(text=format_currency(summary['avg_per_transaction']))
        self.products_sold_card.config(text=str(summary['total_products_sold']))

        payment_breakdown = self.report_service.get_payment_breakdown(context)
        for item in self.payment_tree.get_children():
            self.payment_tree.delete(item)
        if payment_breakdown:
            for row in payment_breakdown:
                self.payment_tree.insert(
                    '',
                    'end',
                    values=(row['method'], row['transaction_count'], format_currency(row['revenue']))
                )
        else:
            self.payment_tree.insert('', 'end', values=('Không có dữ liệu', 0, format_currency(0)))

        top_products = self.report_service.get_top_products_by_quantity(context)
        
        self.top_products_text.delete(1.0, tk.END)
        if top_products:
            for i, row in enumerate(top_products, 1):
                self.top_products_text.insert(
                    tk.END,
                    f"{i}. {row['product_name']}\n"
                    f"    Số lượng: {row['quantity']} SP\n"
                    f"    Doanh thu: {format_currency(row['revenue'])}\n\n"
                )
        else:
            self.top_products_text.insert(1.0, "Chưa có dữ liệu bán hàng\n")

        top_revenue_products = self.report_service.get_top_products_by_revenue(context)

        self.top_revenue_text.delete(1.0, tk.END)
        if top_revenue_products:
            for i, row in enumerate(top_revenue_products, 1):
                self.top_revenue_text.insert(
                    tk.END,
                    f"{i}. {row['product_name']}\n"
                    f"    Doanh thu: {format_currency(row['revenue'])}\n"
                    f"    Số lượng: {row['quantity']} SP\n\n"
                )
        else:
            self.top_revenue_text.insert(1.0, "Chưa có dữ liệu doanh thu sản phẩm\n")
        
        low_stock_products = self.report_service.get_low_stock_products()
        
        self.low_stock_text.delete(1.0, tk.END)
        if low_stock_products:
            for row in low_stock_products:
                name = row['name']
                stock = row['stock']
                status = "🔴 NGUY HIỂM" if stock < 3 else "🟡 CẢI THIỆN"
                self.low_stock_text.insert(tk.END, f"• {name}\n  Còn: {stock} {status}\n\n")
        else:
            self.low_stock_text.insert(1.0, "Không có sản phẩm cần nhập thêm\n")

    def draw_trend(self, event=None):
        from modules.styles import COLORS, FONT
        canvas = self.trend_canvas
        canvas.delete('all')
        width = max(canvas.winfo_width(), 400)
        if not self.trend_rows:
            canvas.create_text(width/2, 80, text='Chưa có giao dịch trong kỳ đã chọn', fill=COLORS['text_secondary'], font=FONT['body'])
            return
        maximum = max((abs(amount) for _, amount in self.trend_rows), default=0) or 1
        step = (width-24) / len(self.trend_rows)
        canvas.create_line(12,80,width-12,80,fill=COLORS['border'])
        for index, (day, amount) in enumerate(self.trend_rows):
            x = 12 + step * index
            y = 80 - 48 * amount / maximum
            canvas.create_rectangle(x+step*.2, min(y,80), x+step*.8, max(y,80), fill=COLORS['primary'] if amount>=0 else COLORS['danger'], outline='')
            short = f'{amount/1000000:.1f}tr' if abs(amount) >= 1000000 else f'{amount/1000:.0f}k' if abs(amount) >= 1000 else str(int(amount))
            canvas.create_text(x+step/2, y-10 if amount>=0 else y+10, text=short, font=FONT['caption'], fill=COLORS['text_primary'])
            canvas.create_text(x+step/2, 139, text=day[8:10]+'/'+day[5:7], font=FONT['caption'], fill=COLORS['text_secondary'])

    def load_transaction_history(self):
        """Tải lịch sử giao dịch"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        context = self.get_current_report_context()
        transactions = self.report_service.get_transactions(context, limit=50)
        
        for trans in transactions:
            formatted_date = self._format_transaction_date(trans['transaction_date'])
            self.history_tree.insert(
                '',
                'end',
                values=(
                    f"{trans['id']} (hoàn #{trans['refund_of']})" if trans['refund_of'] else trans['id'],
                    formatted_date,
                    format_currency(trans['subtotal_amount']),
                    format_currency(trans['discount_amount']),
                    format_currency(trans['total_amount']),
                    trans['payment_method']
                )
            )

    def export_pdf(self):
        """Xuất báo cáo doanh thu theo kỳ hiện tại ra PDF."""
        try:
            context = self.get_current_report_context()
            report_data = self.report_service.get_report_data(context, transaction_limit=None)
            output_path = self.report_exporter.export(report_data)
            messagebox.showinfo("Xuất PDF thành công", f"Đã xuất báo cáo doanh thu:\n{output_path}")
            self._set_status(f"Đã xuất PDF: {Path(output_path).name}")
        except Exception as exc:
            logger.exception("PDF export failed")
            messagebox.showerror("Lỗi xuất PDF", f"Không thể xuất PDF:\n{exc}")
            self._set_status("Xuất PDF lỗi", is_error=True)

    def export_csv(self):
        """Xuất báo cáo hiện tại ra CSV."""
        try:
            context = self.get_current_report_context()
            report_data = self.report_service.get_report_data(context, transaction_limit=None)
            output_path = self.table_exporter.export_csv(report_data)
            messagebox.showinfo("Xuất CSV thành công", f"Đã xuất báo cáo CSV:\n{output_path}")
            self._set_status(f"Đã xuất CSV: {Path(output_path).name}")
        except Exception as exc:
            logger.exception("CSV export failed")
            messagebox.showerror("Lỗi xuất CSV", f"Không thể xuất CSV:\n{exc}")
            self._set_status("Xuất CSV lỗi", is_error=True)

    def export_excel(self):
        """Xuất báo cáo hiện tại ra Excel nếu có openpyxl."""
        try:
            context = self.get_current_report_context()
            report_data = self.report_service.get_report_data(context, transaction_limit=None)
            output_path = self.table_exporter.export_excel(report_data)
            messagebox.showinfo("Xuất Excel thành công", f"Đã xuất báo cáo Excel:\n{output_path}")
            self._set_status(f"Đã xuất Excel: {Path(output_path).name}")
        except Exception as exc:
            logger.exception("Excel export failed")
            messagebox.showerror("Lỗi xuất Excel", f"Không thể xuất Excel:\n{exc}")
            self._set_status("Xuất Excel lỗi", is_error=True)

    def _format_transaction_date(self, value):
        try:
            return datetime.fromisoformat(str(value)).strftime('%d/%m/%Y %H:%M')
        except Exception:
            return str(value)
