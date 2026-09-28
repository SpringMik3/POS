"""Prepare POS reconciliation data; no statutory tax calculation or filing."""
import json
from html import escape
from datetime import datetime

from modules.report_exporter import ReportDataService
from modules.utils import format_currency


PROFILE_FIELDS = {
    'name': 'Tên người nộp thuế / Cơ sở kinh doanh',
    'tax_id': 'Mã số thuế',
    'address': 'Địa chỉ kinh doanh',
    'representative': 'Người đại diện',
    'phone': 'Điện thoại',
    'office': 'Cơ quan thuế quản lý',
}
NOTICE = ('Bảng hỗ trợ đối chiếu số liệu POS, không phải tờ khai thuế chính thức. '
          'Chưa xác định doanh thu tính thuế hay số thuế phải nộp. '
          'Cần đối chiếu hóa đơn, hoàn trả, doanh thu ngoài POS và thời điểm ghi nhận trước khi kê khai. '
          'COD được POS ghi nhận khi Đã thu COD; phí ship không nằm trong doanh thu này. '
          'Phiếu hoàn được ghi âm vào ngày hoàn, không sửa ngày bán gốc.')


class TaxService:
    def __init__(self, conn):
        self.conn = conn
        self.reports = ReportDataService(conn)
        conn.execute('CREATE TABLE IF NOT EXISTS tax_profile (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
        conn.commit()

    def load_profile(self):
        row = self.conn.execute('SELECT data FROM tax_profile WHERE id=1').fetchone()
        return json.loads(row[0]) if row else {}

    def save_profile(self, profile):
        cleaned = {key: str(profile.get(key, '')).strip() for key in PROFILE_FIELDS}
        if not cleaned['name'] or not cleaned['tax_id']:
            raise ValueError('Vui lòng nhập tên người nộp thuế và mã số thuế.')
        self.conn.execute('INSERT INTO tax_profile(id,data) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                          (json.dumps(cleaned, ensure_ascii=False),))
        self.conn.commit()

    def collect(self, start, end):
        if not start.strip() or not end.strip():
            raise ValueError('Vui lòng nhập đủ ngày bắt đầu và kết thúc kỳ đối chiếu.')
        context = self.reports.build_range_period(start, end)
        pending = self.conn.execute("SELECT status, COUNT(*), COALESCE(SUM(total),0), COALESCE(SUM(fee),0) FROM delivery_orders WHERE status IN ('Chờ giao','Đang giao','Đã giao','Giao thất bại','Chờ hoàn hàng') GROUP BY status").fetchall()
        return dict(period=context.label, summary=self.reports.get_summary(context),
                    payments=self.reports.get_payment_breakdown(context),
                    transactions=self.reports.get_transactions(context, limit=None), pending=pending)

    @staticmethod
    def render_html(data, profile, notes=''):
        def e(value):
            return escape(str(value))
        def table(headers, rows):
            return '<table><thead><tr>' + ''.join(f'<th>{e(h)}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{e(v)}</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table>'
        summary = data['summary']
        profile_rows = [(label, profile.get(key, '')) for key, label in PROFILE_FIELDS.items()]
        totals = [('Trước giảm giá', format_currency(summary['subtotal_revenue'])),
                  ('Giảm giá', format_currency(summary['total_discount'])),
                  ('Doanh thu POS sau giảm', format_currency(summary['total_revenue'])),
                  ('Chứng từ bán + hoàn', summary['transaction_count']),
                  ('Tiền hoàn trong kỳ', format_currency(summary['refunded_amount']))]
        transactions = [(f"{t['id']} (hoàn #{t['refund_of']})" if t.get('refund_of') else t['id'], t['transaction_date'], t['payment_method'], format_currency(t['subtotal_amount']),
                         format_currency(t['discount_amount']), format_currency(t['total_amount'])) for t in data['transactions']]
        pending = [(status, count, format_currency(amount), format_currency(fee)) for status, count, amount, fee in data['pending']]
        return ('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Bảng đối chiếu POS</title>'
                '<style>body{font:14px system-ui;color:#1e293b;max-width:1100px;margin:40px auto;padding:0 24px}h1{color:#2563eb}table{border-collapse:collapse;width:100%;margin:18px 0}td,th{padding:10px;border:1px solid #e2e8f0;text-align:left}th{background:#f1f5f9}aside{background:#eff6ff;padding:16px;line-height:1.6}pre{white-space:pre-wrap;font:inherit}thead{display:table-header-group}@media print{body{margin:0;font-size:11px}tr{break-inside:avoid}}</style>'
                f'<h1>Bảng hỗ trợ đối chiếu khai thuế</h1><p>{e(data["period"])}</p>'
                f'<p>Lập lúc {datetime.now():%d/%m/%Y %H:%M}</p><aside>{e(NOTICE)}</aside>'
                '<h2>Thông tin người nộp thuế</h2>' + table(['Thông tin', 'Nội dung'], profile_rows)
                + '<h2>Tổng hợp trong kỳ</h2>' + table(['Chỉ tiêu', 'Giá trị'], totals)
                + '<h2>COD chưa thu tại thời điểm xuất (mọi kỳ)</h2>' + table(['Trạng thái', 'Số đơn', 'Tiền hàng', 'Phí ship'], pending)
                + '<h2>Ghi chú đối chiếu</h2><pre>' + e(notes) + '</pre>'
                + '<h2>Toàn bộ giao dịch trong kỳ</h2>' + table(['Mã', 'Ngày giờ', 'Thanh toán', 'Trước giảm', 'Giảm', 'Sau giảm'], transactions)
                + '</html>')
