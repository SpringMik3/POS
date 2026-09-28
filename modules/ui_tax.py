import calendar
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from modules.services.tax_service import TaxService, PROFILE_FIELDS, NOTICE
from modules.styles import COLORS, FONT, button_style, card_style, entry_style, create_scrollable_frame, configure_treeview_style
from modules.utils import format_currency


class TaxPanel:
    def __init__(self, parent, db, colors):
        self.parent = parent
        self.service = TaxService(db.conn)
        self.profile = {key: tk.StringVar(value=self.service.load_profile().get(key, '')) for key in PROFILE_FIELDS}
        today = date.today()
        self.start = tk.StringVar(value=today.replace(day=1).isoformat())
        self.end = tk.StringVar(value=today.isoformat())
        shell, body = create_scrollable_frame(parent, bg=COLORS['background'])
        shell.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        header = tk.Frame(body, bg=COLORS['background'], padx=18, pady=16)
        header.grid(row=0, column=0, sticky='ew')
        tk.Label(header, text='Hỗ trợ khai thuế', font=FONT['title'], bg=COLORS['background'], fg=COLORS['text_primary']).pack(side='left')
        tk.Button(header, text='Xuất bản đối chiếu', command=self.export, **button_style('primary')).pack(side='right')
        tk.Label(body, text=NOTICE, wraplength=980, justify='left', font=FONT['body_small'],
                 bg=COLORS['primary_light'], fg=COLORS['primary_dark'], padx=16, pady=12).grid(row=1, column=0, sticky='ew', padx=18)
        profile = tk.Frame(body, **card_style())
        profile.grid(row=2, column=0, sticky='ew', padx=18, pady=12)
        for col in (0, 1):
            profile.columnconfigure(col, weight=1)
        tk.Label(profile, text='01  Hồ sơ người nộp thuế', font=FONT['subtitle'], bg=COLORS['surface'], fg=COLORS['text_primary']).grid(row=0, column=0, sticky='w', pady=(0, 10))
        tk.Button(profile, text='Lưu hồ sơ', command=self.save_profile, **button_style('secondary', compact=True)).grid(row=0, column=1, sticky='e')
        for index, (key, label) in enumerate(PROFILE_FIELDS.items()):
            row, col = divmod(index, 2)
            tk.Label(profile, text=label, font=FONT['body_small'], bg=COLORS['surface']).grid(row=row*2+1, column=col, sticky='w', padx=(0, 10), pady=(8, 3))
            tk.Entry(profile, textvariable=self.profile[key], width=24, **entry_style()).grid(row=row*2+2, column=col, sticky='ew', padx=(0, 12), ipady=3)
        period = tk.Frame(body, **card_style())
        period.grid(row=3, column=0, sticky='ew', padx=18, pady=(0, 12))
        tk.Label(period, text='02  Kỳ đối chiếu', font=FONT['subtitle'], bg=COLORS['surface']).pack(anchor='w')
        controls = tk.Frame(period, bg=COLORS['surface'])
        controls.pack(fill='x', pady=(12, 0))
        for label, var in [('Từ ngày', self.start), ('Đến ngày', self.end)]:
            tk.Label(controls, text=label, font=FONT['body_small'], bg=COLORS['surface']).pack(side='left', padx=(0, 6))
            tk.Entry(controls, textvariable=var, width=12, **entry_style()).pack(side='left', padx=(0, 12), ipady=3)
        for label, mode in [('Tháng này', 'month'), ('Quý này', 'quarter'), ('Năm nay', 'year')]:
            tk.Button(controls, text=label, command=lambda m=mode: self.quick_period(m), **button_style('secondary', compact=True)).pack(side='left', padx=3)
        tk.Button(controls, text='Tổng hợp', command=self.refresh, **button_style('primary', compact=True)).pack(side='right')
        self.status = tk.Label(period, text='Ngày: YYYY-MM-DD', font=FONT['caption'], bg=COLORS['surface'], fg=COLORS['text_secondary'])
        self.status.pack(anchor='w', pady=(8, 0))
        results = tk.Frame(body, **card_style())
        results.grid(row=4, column=0, sticky='ew', padx=18, pady=(0, 12))
        self.total = tk.Label(results, font=FONT['subtitle'], bg=COLORS['surface'], fg=COLORS['primary'], anchor='w')
        self.total.pack(fill='x', pady=(0, 12))
        configure_treeview_style('Tax.Treeview', 'report')
        self.tree = ttk.Treeview(results, columns=('method', 'count', 'amount'), show='headings', height=5, style='Tax.Treeview')
        for key, label in [('method', 'Phương thức thanh toán'), ('count', 'Số giao dịch'), ('amount', 'Doanh thu POS sau giảm (đ)')]:
            self.tree.heading(key, text=label)
            self.tree.column(key, anchor='w' if key == 'method' else 'e', width=230)
        self.tree.pack(fill='x')
        self.pending = tk.Label(results, font=FONT['body_small'], bg=COLORS['surface'], fg=COLORS['text_secondary'], anchor='w', justify='left')
        self.pending.pack(fill='x', pady=(12, 0))
        tk.Label(results, text='Ghi chú đối chiếu (đưa vào bản xuất)', font=FONT['label'], bg=COLORS['surface']).pack(anchor='w', pady=(16, 6))
        self.notes = tk.Text(results, height=4, font=FONT['body'], relief='solid', bd=1)
        self.notes.pack(fill='x')
        self.refresh()

    def quick_period(self, mode):
        today = date.today()
        first = 1 if mode == 'year' else (today.month-1)//3*3+1 if mode == 'quarter' else today.month
        last = 12 if mode == 'year' else first+2 if mode == 'quarter' else first
        self.start.set(date(today.year, first, 1).isoformat())
        self.end.set(date(today.year, last, calendar.monthrange(today.year, last)[1]).isoformat())
        self.refresh()

    def refresh(self):
        try:
            data = self.service.collect(self.start.get(), self.end.get())
            summary = data['summary']
            self.total.config(text=f"Doanh thu POS sau hoàn: {format_currency(summary['total_revenue'])}   ·   {summary['transaction_count']} chứng từ bán + hoàn")
            self.tree.delete(*self.tree.get_children())
            for row in data['payments']:
                self.tree.insert('', 'end', values=(row['method'], row['transaction_count'], format_currency(row['revenue'])))
            if not data['payments']:
                self.tree.insert('', 'end', values=('Chưa có giao dịch trong kỳ', 0, '0'))
            pending_total = sum(row[2] for row in data['pending'])
            self.pending.config(text=f"Trước giảm: {format_currency(summary['subtotal_revenue'])}   ·   Giảm giá: {format_currency(summary['total_discount'])}\nCOD chưa thu hiện tại (mọi kỳ): {format_currency(pending_total)} tiền hàng — chưa nằm trong giao dịch POS.")
            self.status.config(text=data['period'], fg=COLORS['text_secondary'])
            return data
        except ValueError as exc:
            self.total.config(text='Chưa tổng hợp · Kiểm tra lại kỳ đối chiếu')
            self.tree.delete(*self.tree.get_children())
            self.pending.config(text='')
            self.status.config(text=str(exc), fg=COLORS['danger'])
            return None

    def save_profile(self):
        try:
            self.service.save_profile({k: v.get() for k, v in self.profile.items()})
            messagebox.showinfo('Đã lưu', 'Đã lưu hồ sơ người nộp thuế.', parent=self.parent)
        except ValueError as exc:
            messagebox.showerror('Kiểm tra hồ sơ', str(exc), parent=self.parent)

    def export(self):
        data = self.refresh()
        if data is None:
            return
        profile = {k: v.get().strip() for k, v in self.profile.items()}
        if not profile['name'] or not profile['tax_id']:
            messagebox.showwarning('Thiếu hồ sơ', 'Nhập tên người nộp thuế và mã số thuế trước khi xuất.', parent=self.parent)
            return
        path = filedialog.asksaveasfilename(parent=self.parent, title='Lưu bản đối chiếu', defaultextension='.html', filetypes=[('Bản đối chiếu HTML', '*.html')], initialfile=f'doi_chieu_thue_{date.today().isoformat()}.html')
        if not path:
            return
        try:
            Path(path).write_text(self.service.render_html(data, profile, self.notes.get('1.0', 'end').strip()), encoding='utf-8')
            messagebox.showinfo('Đã xuất', f'Đã lưu: {path}\nMở bằng trình duyệt, chọn In để lưu PDF hoặc in giấy.', parent=self.parent)
        except OSError as exc:
            messagebox.showerror('Không thể lưu', str(exc), parent=self.parent)
