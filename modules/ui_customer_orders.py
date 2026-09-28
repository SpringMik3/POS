"""Small-store workflows. No accounts or permission roles."""
import json
import tkinter as tk
from tkinter import ttk, messagebox
from modules.styles import COLORS as C, FONT, button_style, card_style, configure_treeview_style, create_scrollable_frame
from modules.utils import format_currency as currency
from modules.services.customer_service import CustomerService
from modules.services.return_service import ReturnService
from modules.services.order_service import OrderService, money


def label(parent, text, title=False):
    widget = tk.Label(parent, text=text, bg=C['surface'], fg=C['text_primary'],
                      font=FONT['subtitle'] if title else FONT['body_small'], anchor='w', justify='left', wraplength=680)
    widget.pack(fill='x', pady=(0, 10) if title else (4, 4))
    widget.bind('<Configure>',lambda event: widget.configure(wraplength=max(120,event.width-4)))
    return widget


def button(parent, text, command, primary=False, side='left'):
    widget = tk.Button(parent, text=text, command=command,
                       **button_style('primary' if primary else 'secondary', compact=True))
    widget.pack(side=side, padx=(0, 8), pady=4)
    return widget


def field(parent, title, value='', choices=None):
    label(parent, title)
    var = tk.StringVar(value=value)
    widget = ttk.Combobox(parent, textvariable=var, values=choices, state='readonly') if choices else ttk.Entry(parent, textvariable=var)
    widget.pack(fill='x', ipady=4, pady=(0, 6))
    return var, widget


def table(parent, columns, height=12):
    frame = tk.Frame(parent, bg=C['surface'])
    frame.pack(fill='both', expand=True, pady=8)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show='headings', height=height,
                        selectmode='browse', style='Operations.Treeview')
    for key, title, width in columns:
        tree.heading(key, text=title)
        tree.column(key, width=width, minwidth=60, anchor='w')
    vs = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    hs = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky='nsew')
    vs.grid(row=0, column=1, sticky='ns')
    hs.grid(row=1, column=0, sticky='ew')
    return tree


def modal(parent, title, width=760, height=680):
    window = tk.Toplevel(parent)
    window.title(title)
    window.geometry(f'{width}x{min(height, window.winfo_screenheight()-100)}')
    window.configure(bg=C['background'])
    window.transient(parent.winfo_toplevel())
    window.grab_set()
    footer = tk.Frame(window, bg=C['surface'], padx=18, pady=10)
    footer.pack(side='bottom', fill='x')
    shell, body = create_scrollable_frame(window, bg=C['surface'])
    shell.pack(fill='both', expand=True, padx=18, pady=14)
    return window, body, footer


def customer_dialog(parent, service, customer_id=None, on_saved=None):
    window, body, footer = modal(parent, 'Thông tin khách hàng', 560, 540)
    row = service.get(customer_id) if customer_id else None
    label(body, 'Chỉnh sửa khách hàng' if row else 'Thêm khách hàng', True)
    fields = [field(body, title, (row[index+1] or '') if row else '')[0]
              for index, title in enumerate(('Tên khách hàng *', 'Điện thoại (có thể để trống)', 'Địa chỉ', 'Ghi chú'))]
    def close():
        window.destroy()
        if isinstance(parent,tk.Toplevel) and parent.winfo_exists():
            parent.grab_set()
    window.protocol('WM_DELETE_WINDOW',close)
    def save():
        try:
            saved_id = service.save(*(v.get() for v in fields), customer_id=customer_id)
        except ValueError as exc:
            messagebox.showerror('Kiểm tra thông tin', str(exc), parent=window)
            return
        close()
        if on_saved:
            on_saved(saved_id)
    button(footer, 'Lưu khách hàng', save, True, 'right')
    button(footer, 'Đóng', close, side='right')
    return window


class CustomerOrdersPanel:
    def __init__(self, parent, db, on_exchange=None):
        self.parent, self.db, self.on_exchange = parent, db, on_exchange
        self.customers = CustomerService(db.conn)
        self.returns = ReturnService(db.conn)
        configure_treeview_style('Operations.Treeview', 'management')
        tabs = self.tabs = ttk.Notebook(parent, style='Modern.TNotebook')
        tabs.pack(fill='both', expand=True, padx=16, pady=16)
        self.pages = []
        for title in ('Khách hàng', 'Đổi trả / Hoàn tiền'):
            frame = tk.Frame(tabs, **card_style())
            tabs.add(frame, text=f'  {title}  ')
            self.pages.append(frame)
        self.build_customers()
        self.build_returns()
        self.refresh()

    def build_customers(self):
        page = self.pages[0]
        label(page, 'Khách hàng', True)
        label(page, 'Lưu khách quen để tra cứu lần mua trước. Khi bán hàng vẫn có thể chọn Khách lẻ.')
        bar = tk.Frame(page, bg=C['surface']); bar.pack(fill='x')
        self.customer_search = tk.StringVar()
        ttk.Entry(bar, textvariable=self.customer_search, width=32).pack(side='left', ipady=5, padx=(0, 12))
        button(bar, 'Tìm tên / điện thoại', self.refresh_customers)
        button(bar, 'Thêm khách hàng', lambda: customer_dialog(page, self.customers, on_saved=lambda _: self.refresh_customers()), True, 'right')
        button(bar, 'Sửa thông tin', self.edit_customer, side='right')
        self.customer_search.trace_add('write', lambda *_: self.refresh_customers())
        self.customer_tree = table(page, [('id','Mã',60),('name','Khách hàng',200),('phone','Điện thoại',140),('count','Số đơn bán',100),('total','Mua ròng sau hoàn',170)], 9)
        self.customer_tree.bind('<<TreeviewSelect>>', self.customer_history)
        self.customer_tree.bind('<Double-1>', lambda _: self.edit_customer())
        self.customer_detail = label(page, 'Chọn khách hàng để xem lịch sử giao dịch và đơn COD.')
        self.customer_history_tree = table(page, [('id','Chứng từ',90),('date','Ngày giờ',170),('type','Nội dung / Trạng thái',220),('amount','Số tiền',160),('method','Thanh toán',130)], 7)

    def refresh_customers(self):
        self.customer_tree.delete(*self.customer_tree.get_children())
        for row in self.customers.list(self.customer_search.get()):
            self.customer_tree.insert('', 'end', iid=str(row[0]), values=(row[0],row[1],row[2],row[5],currency(row[6])))
        self.customer_history_tree.delete(*self.customer_history_tree.get_children())
        self.customer_detail.config(text='Chọn khách hàng để xem lịch sử giao dịch và đơn COD.')

    def edit_customer(self):
        selected = self.customer_tree.selection()
        if selected:
            customer_dialog(self.parent, self.customers, int(selected[0]), lambda _: self.refresh_customers())
        else:
            messagebox.showinfo('Chọn khách hàng', 'Chọn một khách trong danh sách trước.', parent=self.parent)

    def customer_history(self, *_):
        self.customer_history_tree.delete(*self.customer_history_tree.get_children())
        selected = self.customer_tree.selection()
        if not selected:
            return
        customer_id = int(selected[0])
        row = self.customers.get(customer_id)
        self.customer_detail.config(text=f'{row[1]} · {row[3] or "Chưa có địa chỉ"} · {row[4] or "Không có ghi chú"}')
        for item in self.customers.history(customer_id):
            self.customer_history_tree.insert('', 'end', values=(f'#{item[0]}',item[1],item[2],currency(item[3]),item[4]))
        for item in self.db.conn.execute('SELECT id,created_at,status,total+fee FROM delivery_orders WHERE customer_id=? ORDER BY id DESC', (customer_id,)):
            self.customer_history_tree.insert('', 'end', values=(f'COD #{item[0]}',item[1],item[2],currency(item[3]),'Thu hộ gồm ship'))

    def build_returns(self):
        page = self.pages[1]
        label(page, 'Đổi trả & hoàn tiền', True)
        label(page, 'Chọn đơn gốc → chọn hàng trả → kiểm tra tiền hoàn. Đổi hàng: hoàn đơn cũ rồi lập đơn bán mới có liên kết.')
        bar = tk.Frame(page, bg=C['surface']); bar.pack(fill='x')
        self.return_search = tk.StringVar()
        ttk.Entry(bar, textvariable=self.return_search, width=35).pack(side='left', ipady=5, padx=(0,12))
        button(bar, 'Tìm mã đơn / khách / điện thoại', self.refresh_returns)
        button(bar, 'Tạo phiếu đổi trả', self.open_return, True, 'right')
        self.sale_tree = table(page, [('id','Đơn gốc',85),('date','Ngày giờ',170),('name','Khách hàng',200),('total','Thanh toán ban đầu',170),('refund','Đã hoàn',150),('method','Phương thức',140)])
        self.sale_tree.bind('<Double-1>', lambda _: self.open_return())
        label(page, 'Hiển thị tối đa 200 đơn phù hợp. Phiếu hoàn giữ nguyên đơn gốc và ghi giảm doanh thu vào ngày hoàn.')

    def refresh_returns(self):
        self.sale_tree.delete(*self.sale_tree.get_children())
        for row in self.returns.sales(self.return_search.get().strip()):
            self.sale_tree.insert('', 'end', iid=str(row[0]), values=(*row[:3],currency(row[3]),currency(row[4]),row[5]))

    def open_return(self):
        selected = self.sale_tree.selection()
        if not selected:
            messagebox.showinfo('Chọn đơn', 'Chọn đơn gốc cần đổi trả.', parent=self.parent)
            return
        sale_id = int(selected[0])
        try:
            lines = self.returns.lines(sale_id)
        except ValueError as exc:
            messagebox.showerror('Không thể đổi trả', str(exc), parent=self.parent)
            return
        window, body, footer = modal(self.parent, f'Đổi trả đơn #{sale_id}', 900, 760)
        label(body, f'Đổi trả đơn #{sale_id}', True)
        label(body, 'Tiền hoàn tính theo giá và giảm giá của đơn gốc. Hàng hỏng: bỏ chọn Nhập lại kho.')
        tree = table(body, [('name','Sản phẩm',240),('bought','Đã mua',80),('returned','Đã trả',80),('qty','Trả lần này',100),('stock','Nhập kho',100)], 6)
        selections = {}
        def redraw():
            tree.delete(*tree.get_children())
            for line in lines:
                chosen = selections.get(line['id'], {})
                tree.insert('', 'end', iid=str(line['id']), values=(line['name'],line['quantity'],line['returned'],chosen.get('quantity',0),'Có' if chosen.get('restock') else '—'))
            try:
                quote = self.returns.quote(sale_id, selections)
                total_label.config(text='Tiền cần hoàn: ' + currency(sum(r['amount'] for r in quote)))
            except ValueError as exc:
                total_label.config(text=str(exc))
        qty, _ = field(body, 'Số lượng trả của dòng đang chọn', '1')
        restock = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text='Hàng đã nhận lại và còn bán được → nhập lại kho', variable=restock).pack(anchor='w', pady=6)
        actions = tk.Frame(body,bg=C['surface']); actions.pack(fill='x')
        def choose():
            if not tree.selection():
                return
            key = int(tree.selection()[0])
            candidate = dict(selections)
            candidate[key] = dict(quantity=qty.get(), restock=restock.get())
            try:
                self.returns.quote(sale_id, candidate)
            except ValueError as exc:
                messagebox.showerror('Kiểm tra số lượng', str(exc), parent=window)
                return
            selections.update(candidate)
            redraw()
        def all_remaining():
            selections.clear()
            selections.update({r['id']:dict(quantity=r['quantity']-r['returned'],restock=restock.get()) for r in lines if r['quantity']>r['returned']})
            redraw()
        def remove():
            if tree.selection():
                selections.pop(int(tree.selection()[0]), None)
                redraw()
        button(actions,'Áp dụng dòng',choose,True)
        button(actions,'Bỏ dòng',remove)
        button(actions,'Trả toàn bộ phần còn lại',all_remaining)
        method, _ = field(body,'Phương thức hoàn tiền thực tế','Tiền mặt', ['Tiền mặt','Chuyển khoản','Thẻ'])
        reason, _ = field(body,'Lý do đổi trả / hủy đơn *')
        total_label = label(body, 'Chưa chọn sản phẩm trả.', True)
        label(body, 'Các phiếu hoàn đã lưu của đơn này')
        history = table(body,[('id','Phiếu hoàn',90),('date','Ngày',155),('amount','Tiền hoàn',135),('reason','Lý do',340)],3)
        for record in self.db.conn.execute('SELECT id,transaction_date,-total_amount,reason FROM transactions WHERE refund_of=? ORDER BY id DESC',(sale_id,)):
            history.insert('','end',values=(record[0],record[1],currency(record[2]),record[3]))
        def submit(exchange=False):
            try:
                quote = self.returns.quote(sale_id, selections)
                total = sum(r['amount'] for r in quote)
                if not reason.get().strip():
                    raise ValueError('Nhập lý do đổi trả.')
                if exchange and self.on_exchange and not self.on_exchange(sale_id, check_only=True):
                    return
                if not messagebox.askyesno('Xác nhận phiếu hoàn',
                    f'Hoàn {currency(total)} qua {method.get()} cho đơn #{sale_id}.\nBạn đã thực hiện hoàn tiền và kiểm tra tình trạng hàng?\nỨng dụng chỉ ghi nhận, không tự chuyển tiền.', parent=window):
                    return
                refund_id, total = self.returns.refund(sale_id, selections, method.get(), reason.get(), expected_total=total)
            except Exception as exc:
                messagebox.showerror('Chưa lưu được phiếu hoàn',str(exc),parent=window)
                return
            window.destroy()
            self.refresh()
            messagebox.showinfo('Đã lưu', f'Phiếu hoàn #{refund_id}: {currency(total)}.\nĐơn gốc #{sale_id} được giữ để đối chiếu.', parent=self.parent)
            if exchange and self.on_exchange:
                self.on_exchange(sale_id)
        button(footer,'Lưu phiếu hoàn',submit,True,'right')
        if self.on_exchange:
            button(footer,'Hoàn & lập đơn đổi',lambda: submit(True),side='right')
        button(footer,'Đóng',window.destroy,side='right')
        redraw()

    def refresh(self):
        self.refresh_customers()
        self.refresh_returns()


class CodPanel:
    """Independent COD page; opening it does not require a cart or checkout."""
    def __init__(self, parent, db):
        self.parent, self.db = parent, db
        self.orders = OrderService(db.conn)
        configure_treeview_style('Operations.Treeview', 'management')
        self.page = tk.Frame(parent, **card_style())
        self.page.pack(fill='both', expand=True, padx=16, pady=16)
        self.build_orders()
        self.refresh()

    def build_orders(self):
        page = self.page
        label(page,'Giao hàng & đối soát COD',True)
        self.cod_summary = label(page,'')
        bar = tk.Frame(page,bg=C['surface']); bar.pack(fill='x')
        self.order_search = tk.StringVar()
        ttk.Entry(bar,textvariable=self.order_search,width=25).pack(side='left',ipady=5,padx=(0,8))
        self.order_status = tk.StringVar(value='Tất cả')
        ttk.Combobox(bar,textvariable=self.order_status,state='readonly',width=20,
            values=['Tất cả', *OrderService.TRANSITIONS, 'Đã thu COD','Đã hoàn hàng','Đã hủy']).pack(side='left',padx=(0,8))
        button(bar,'Lọc tên / SĐT / vận đơn',self.refresh_orders)
        button(bar,'Xử lý đơn / Đối soát',self.open_order,True,'right')
        self.order_tree = table(page,[('id','Mã',60),('name','Người nhận',160),('phone','Điện thoại',130),('total','Thu hộ gồm ship',150),('status','Trạng thái',150),('carrier','Hãng giao',120),('tracking','Vận đơn',140)])
        self.order_tree.bind('<Double-1>',lambda _: self.open_order())
        label(page,'Tạo đơn COD tại màn hình thanh toán. Phí hãng và tiền thực nhận được nhập từ bảng đối soát của hãng.')

    def refresh_orders(self):
        self.order_tree.delete(*self.order_tree.get_children())
        rows = self.orders.list_orders()
        term = self.order_search.get().strip().casefold()
        for row in rows:
            if self.order_status.get() != 'Tất cả' and row[4] != self.order_status.get():
                continue
            if term and term not in ' '.join(str(x or '') for x in row[:7]).casefold():
                continue
            self.order_tree.insert('', 'end', iid=str(row[0]),values=(*row[:3],currency(row[3]),*row[4:7]))
        pending = self.db.conn.execute("SELECT COALESCE(SUM(total+fee),0) FROM delivery_orders WHERE status='Đã giao'").fetchone()[0]
        delta = self.db.conn.execute("SELECT COALESCE(SUM(received_amount-(total+fee-carrier_fee)),0) FROM delivery_orders WHERE status='Đã thu COD' AND received_amount IS NOT NULL").fetchone()[0]
        self.cod_summary.config(text=f'Đã giao, chờ đối soát: {currency(pending)} thu hộ trước phí · Chênh lệch đã đối soát: {currency(delta)} (mọi kỳ)')

    def open_order(self):
        selected = self.order_tree.selection()
        if not selected:
            messagebox.showinfo('Chọn đơn','Chọn đơn COD để xử lý.',parent=self.parent)
            return
        order_id = int(selected[0]); data = self.orders.details(order_id)
        window, body, footer = modal(self.parent,f'COD #{order_id}',850,790)
        label(body,f'COD #{order_id} · {data["status"]}',True)
        label(body,f'{data["recipient"]} · {data["phone"]}\n{data["address"]}\nTiền hàng: {currency(data["total"])} · Ship khách trả: {currency(data["fee"])}')
        label(body,'\n'.join(f'{i["name"]} × {i["quantity"]}' for i in json.loads(data['items'])))
        carrier,_ = field(body,'Đơn vị giao hàng',data['carrier'] or '')
        tracking,_ = field(body,'Mã vận đơn',data['tracking'] or '')
        shipping_note,_ = field(body,'Ghi chú giao hàng',data['note'] or '')
        allowed = self.orders.TRANSITIONS.get(data['status'],())
        status,status_widget = field(body,'Bước xử lý tiếp theo',allowed[0] if allowed else data['status'],list(allowed) or [data['status']])
        fee,_ = field(body,'Phí hãng khấu trừ / phí hoàn (đ)',str(data['carrier_fee'] or 0))
        received,_ = field(body,'Tiền hãng thực chuyển về (đ)',str(data['received_amount']) if data['received_amount'] is not None else '')
        expected_label = label(body,'')
        def preview(*_):
            try:
                expected = data['total']+data['fee']-money(fee.get())
                text = f'Dự kiến nhận sau phí: {currency(expected)}'
                if received.get().strip():
                    text += f' · Chênh lệch: {currency(money(received.get())-expected)}'
                expected_label.config(text=text)
            except ValueError:
                expected_label.config(text='Kiểm tra số tiền phí và tiền thực nhận.')
        fee.trace_add('write',preview); received.trace_add('write',preview); preview()
        note,_ = field(body,'Lý do / ghi chú đối soát (bắt buộc khi lệch tiền)',data['settlement_note'] or '')
        restock = tk.BooleanVar(value=True)
        ttk.Checkbutton(body,text='Khi xác nhận Đã hoàn hàng: hàng đã về và còn bán được, nhập lại kho',variable=restock).pack(anchor='w',pady=6)
        history = table(body,[('date','Thời gian',150),('status','Trạng thái',150),('note','Ghi chú',420)],4)
        for row in self.orders.history(order_id):
            history.insert('','end',values=(row[0],row[2],row[3]))
        if data['status']=='Đã thu COD':
            label(body,'Đơn đã thu COD: nếu khách trả hàng, tạo phiếu hoàn từ giao dịch #' + str(data['transaction_id']))
        def save_tracking():
            try:
                self.orders.save_tracking(order_id,carrier.get(),tracking.get(),shipping_note.get())
            except Exception as exc:
                messagebox.showerror('Chưa lưu được',str(exc),parent=window); return
            window.destroy(); self.refresh_orders()
        def process():
            target = status.get()
            if not messagebox.askyesno('Xác nhận xử lý',f'Đơn #{order_id}: {data["status"]} → {target}\n{expected_label.cget("text") if target=="Đã thu COD" else ""}\nĐã kiểm tra tiền và tình trạng hàng thực tế?',parent=window):
                return
            try:
                self.orders.update(order_id,target,tracking.get(),fee.get(),received.get() or None,note.get(),restock.get(),carrier.get(),shipping_note.get())
            except Exception as exc:
                messagebox.showerror('Chưa cập nhật được',str(exc),parent=window); return
            window.destroy(); self.refresh()
        if allowed:
            button(footer,'Xác nhận bước xử lý',process,True,'right')
        button(footer,'Chỉ lưu vận đơn / ghi chú',save_tracking,side='right')
        button(footer,'Đóng',window.destroy,side='right')

    def refresh(self):
        self.refresh_orders()
