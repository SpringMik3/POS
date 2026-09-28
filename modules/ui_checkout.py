import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from uuid import uuid4
import webbrowser

from modules.services.order_service import OrderService, money, qr_url
from modules.styles import create_scrollable_frame
from modules.services.customer_service import CustomerService


class CheckoutWindow(tk.Toplevel):
    def __init__(self, panel):
        super().__init__(panel.parent)
        self.panel = panel
        self.orders = OrderService(panel.db.conn)
        self.title('AnnaBeauty • Thanh toán & giao hàng')
        self.geometry(f'820x{min(800, self.winfo_screenheight()-100)}')
        self.minsize(740, 480)
        self.configure(bg='#f1f5f9')
        self.transient(panel.parent)
        self.grab_set()
        panel.scanning_active = False
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.reference = 'AB' + uuid4().hex[:12].upper()
        self.items = []
        for iid in panel.cart_tree.get_children():
            name, qty, price, subtotal = panel.cart_tree.item(iid)['values']
            self.items.append(dict(product_id=panel._product_id_from_cart_iid(iid), name=name,
                                   quantity=int(qty), price=money(price), subtotal=money(subtotal)))
        self.raw_total = sum(i['price'] * i['quantity'] for i in self.items)
        self.vars = {}
        self.label('HOÀN TẤT ĐƠN HÀNG', self, 20, '#0f172a').pack(anchor='w', padx=24, pady=(20, 4))
        self.label(f'{len(self.items)} sản phẩm  •  Nội dung chuyển khoản: {self.reference}', self).pack(anchor='w', padx=24, pady=(0, 12))
        footer = tk.Frame(self, bg='#ffffff', padx=24, pady=14)
        footer.pack(side='bottom', fill='x')
        self.total_label = self.label('', footer, 22, '#047857')
        self.total_label.pack(side='left')
        self.submit = tk.Button(footer, text='Xác nhận thanh toán', command=self.complete,
                                bg='#2563eb', fg='white', relief='flat', padx=18, pady=12, font=('Segoe UI', 11, 'bold'))
        self.submit.pack(side='right')
        shell, body = create_scrollable_frame(self, bg='#f1f5f9')
        shell.pack(fill='both', expand=True, padx=24)
        self.body = body
        summary = self.card('01   Chi tiết thanh toán')
        self.label(f'Tạm tính: {self.raw_total:,.0f} ₫', summary, 12).pack(anchor='w')
        self.field(summary, 'Giảm giá (%)', 'discount', '0')
        self.field(summary, 'Phương thức', 'method', 'Tiền mặt', ['Tiền mặt', 'Thẻ', 'Chuyển khoản', 'COD'])
        self.customer_service = CustomerService(panel.db.conn)
        self.customer_map = {}
        self.customer_combo = self.field(summary, 'Khách hàng (tùy chọn)', 'customer', 'Khách lẻ', ['Khách lẻ'])
        self.reload_customers()
        self.customer_combo.bind('<<ComboboxSelected>>', self.select_customer)
        from modules.ui_customer_orders import customer_dialog
        ttk.Button(summary, text='Thêm khách hàng', command=lambda: customer_dialog(self, self.customer_service,
            on_saved=lambda customer_id: self.reload_customers(customer_id))).pack(anchor='e', pady=4)
        self.exchange_for = getattr(panel, 'exchange_for', None)
        self.link_exchange = tk.BooleanVar(value=self.exchange_for is not None)
        if self.exchange_for:
            ttk.Checkbutton(summary, text=f'Đơn đổi từ #{self.exchange_for} (hoàn tiền cũ đã ghi riêng)', variable=self.link_exchange).pack(anchor='w')
        self.cash = self.card('02   Tiền khách đưa')
        self.field(self.cash, 'Khách đưa (₫)', 'cash', str(self.raw_total))
        self.change = self.label('', self.cash)
        self.change.pack(anchor='w', pady=4)
        self.bank = self.card('02   QR chuyển khoản')
        saved = panel.db.conn.execute('SELECT bank, account, name FROM payment_settings WHERE id=1').fetchone() or ('', '', '')
        for label, key, value in zip(['Mã ngân hàng (VCB, MB, TCB...)', 'Số tài khoản', 'Tên chủ tài khoản'], ['bank', 'account', 'name'], saved):
            self.field(self.bank, label, key, value)
        tk.Button(self.bank, text='Tạo / mở QR thanh toán', command=self.open_qr, relief='flat', bg='#dbeafe', pady=8).pack(fill='x', pady=8)
        self.label('QR mở trên trình duyệt qua VietQR, cần Internet.\nThông tin tài khoản, số tiền và nội dung được gửi tới VietQR.\nKhi đổi giảm giá, hãy tạo lại QR và đối chiếu số tiền nhận thực tế.', self.bank).pack(anchor='w')
        self.verified = tk.BooleanVar(value=False)
        tk.Checkbutton(self.bank, text='Đã kiểm tra và nhận đủ tiền trong tài khoản / máy POS', variable=self.verified, bg='white').pack(anchor='w', pady=6)
        self.shipping = self.card('02   Giao hàng • Thu hộ COD')
        for label, key, value in [('Người nhận *', 'recipient', ''), ('Điện thoại *', 'phone', ''),
                                   ('Địa chỉ đầy đủ *', 'address', ''), ('Phí ship khách trả (₫)', 'fee', '0'),
                                   ('Đơn vị vận chuyển', 'carrier', ''), ('Mã vận đơn (nếu có)', 'tracking', ''),
                                   ('Ghi chú giao hàng', 'note', '')]:
            self.field(self.shipping, label, key, value)
        self.label('Lưu đơn nội bộ và giữ hàng ngay. Chưa tự gửi sang hãng vận chuyển.\nPhí ship được thu hộ, không tính vào doanh thu hàng hóa.', self.shipping).pack(anchor='w', pady=6)
        for key in ('discount', 'cash', 'fee', 'method'):
            self.vars[key].trace_add('write', self.refresh)
        self.refresh()
        if self.exchange_for:
            original = panel.db.conn.execute('SELECT customer_id FROM transactions WHERE id=?', (self.exchange_for,)).fetchone()
            if original and original[0]:
                self.reload_customers(original[0])

    def reload_customers(self, selected_id=None):
        self.customer_map = {f'{r[0]} · {r[1]} · {r[2]}': r[0] for r in self.customer_service.list()}
        self.customer_combo['values'] = ['Khách lẻ', *self.customer_map]
        if selected_id:
            self.vars['customer'].set(next(k for k,v in self.customer_map.items() if v == selected_id))
            if 'recipient' in self.vars:
                self.select_customer()

    def select_customer(self, *_):
        customer_id = self.customer_map.get(self.vars['customer'].get())
        if customer_id:
            row = self.customer_service.get(customer_id)
            for key, value in zip(('recipient','phone','address'), row[1:4]):
                self.vars[key].set(value or '')

    def label(self, text, parent, size=10, color='#475569'):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color, font=('Segoe UI', size), justify='left', anchor='w')

    def card(self, title):
        frame = tk.Frame(self.body, bg='white', padx=18, pady=14)
        frame.pack(fill='x', pady=(0, 12))
        self.label(title, frame, 13, '#0f172a').pack(anchor='w', pady=(0, 10))
        return frame

    def field(self, parent, label, key, value='', choices=None):
        row = tk.Frame(parent, bg='white')
        row.pack(fill='x', pady=4)
        self.label(label, row).pack(side='left')
        var = self.vars[key] = tk.StringVar(value=value)
        widget = ttk.Combobox(row, textvariable=var, values=choices, state='readonly', width=33) if choices else ttk.Entry(row, textvariable=var, width=36)
        widget.pack(side='right', padx=(12, 0), ipady=4)
        return widget

    def totals(self):
        import math
        percent = float(self.vars['discount'].get())
        if not math.isfinite(percent) or not 0 <= percent <= 100:
            raise ValueError('Giảm giá phải từ 0 đến 100%.')
        total = round(self.raw_total * (100-percent)/100)
        fee = money(self.vars['fee'].get()) if self.vars['method'].get() == 'COD' else 0
        return percent, total, fee

    def refresh(self, *_):
        method = self.vars['method'].get()
        self.verified.set(False)
        for frame in (self.cash, self.bank, self.shipping):
            frame.pack_forget()
        if method == 'Tiền mặt':
            self.cash.pack(fill='x', pady=(0, 12))
        elif method in ('Thẻ', 'Chuyển khoản'):
            self.bank.pack(fill='x', pady=(0, 12))
        else:
            self.shipping.pack(fill='x', pady=(0, 12))
        self.submit.config(text='Lên đơn COD' if method == 'COD' else 'Xác nhận thanh toán')
        try:
            _, total, fee = self.totals()
            self.total_label.config(text=f'{total+fee:,.0f} ₫')
            if method == 'Tiền mặt':
                change = money(self.vars['cash'].get()) - total
                self.change.config(text=f'Tiền thừa: {change:,.0f} ₫' if change >= 0 else f'Còn thiếu: {-change:,.0f} ₫')
        except ValueError:
            self.total_label.config(text='Kiểm tra số tiền')

    def open_qr(self):
        try:
            _, total, _ = self.totals()
            bank, account, name = [self.vars[k].get().strip() for k in ('bank', 'account', 'name')]
            url = qr_url(bank, account, name, total, self.reference)
            with self.panel.db.conn:
                self.panel.db.conn.execute('INSERT OR REPLACE INTO payment_settings VALUES (1, ?, ?, ?)', (bank, account, name))
            if not webbrowser.open(url):
                raise ValueError('Không mở được trình duyệt. Vui lòng kiểm tra trình duyệt mặc định.')
        except Exception as exc:
            messagebox.showerror('Không tạo được QR', str(exc), parent=self)

    def close(self):
        self.panel.scanning_active = True
        self.destroy()

    def complete(self):
        try:
            percent, total, fee = self.totals()
            method = self.vars['method'].get()
            customer_id = self.customer_map.get(self.vars['customer'].get())
            exchange_for = self.exchange_for if self.link_exchange.get() else None
            if exchange_for and method == 'COD':
                raise ValueError('Đơn đổi cần thanh toán ngay. Bỏ liên kết đơn đổi nếu muốn tạo một đơn COD riêng.')
            if method == 'Tiền mặt' and money(self.vars['cash'].get()) < total:
                raise ValueError('Tiền khách đưa chưa đủ.')
            if method in ('Thẻ', 'Chuyển khoản') and not self.verified.get():
                raise ValueError('Vui lòng xác nhận đã nhận đủ tiền trước khi hoàn tất.')
            self.submit.config(state='disabled')
            if method == 'COD':
                fields = {k: self.vars[k].get() for k in ('recipient', 'phone', 'address', 'carrier', 'tracking', 'note')}
                order_id = self.orders.create(self.items, percent, fee=fee, customer_id=customer_id, **fields)
                result_message = f'Đã lưu đơn COD #{order_id}. Thu hộ: {total+fee:,.0f} ₫.\nTheo dõi và xử lý tại trang ĐƠN COD.'
                receipt = None
            else:
                result = self.panel.sales_service.checkout(self.items, self.raw_total, percent, method, customer_id=customer_id, exchange_for=exchange_for)
                result_message = f"Đã thanh toán giao dịch #{result['transaction_id']}."
                receipt = dict(id=result['transaction_id'], datetime=datetime.now(), items=self.items,
                               subtotal=self.raw_total, discount_percent=percent,
                               discount_amount=result['discount_amount'], total_amount=result['total_amount'],
                               total_after_discount=result['total_amount'], payment_method=method)
        except Exception as exc:
            self.submit.config(state='normal')
            messagebox.showerror('Chưa thể hoàn tất', str(exc), parent=self)
            return
        # Clear immediately after commit; printer failures must never permit another charge.
        for iid in self.panel.cart_tree.get_children():
            self.panel.cart_tree.delete(iid)
        self.panel.cart.clear()
        self.panel.cart_items.clear()
        self.panel.exchange_for = None
        self.panel.update_total()
        self.close()
        self.panel.load_products()
        self.panel._set_action_status(result_message, 'success')
        if receipt:
            try:
                success, detail = self.panel.printer.print_receipt(receipt)
                if not success:
                    result_message += '\nChưa in được hóa đơn: ' + detail
            except Exception as exc:
                result_message += '\nChưa in được hóa đơn: ' + str(exc)
        messagebox.showinfo('Đã lưu đơn', result_message, parent=self.panel.parent)

