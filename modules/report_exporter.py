from dataclasses import dataclass
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional
import unicodedata

from modules.app_paths import resolve_app_path, resolve_bundle_path
from modules.app_logger import get_logger
from modules.services.inventory_service import InventoryService
from modules.utils import format_currency


logger = get_logger(__name__)


@dataclass(frozen=True)
class ReportPeriod:
    period: str
    year: int
    month: Optional[int]
    day: Optional[int]
    value: str
    label: str
    filename_suffix: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    payment_method: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    category: Optional[str] = None


class ReportDataService:
    def __init__(self, conn):
        self.conn = conn
        self.inventory_service = InventoryService(conn)

    def build_period(self, period, year, month=None, day=None):
        period = (period or 'day').lower()
        year = int(year)

        if period == 'day':
            selected_date = datetime(year, int(month), int(day))
            return ReportPeriod(
                period='day',
                year=selected_date.year,
                month=selected_date.month,
                day=selected_date.day,
                value=selected_date.strftime('%Y-%m-%d'),
                label=selected_date.strftime('Ngày %d/%m/%Y'),
                filename_suffix=selected_date.strftime('%Y_%m_%d'),
            )

        if period == 'month':
            selected_month = datetime(year, int(month), 1)
            return ReportPeriod(
                period='month',
                year=selected_month.year,
                month=selected_month.month,
                day=None,
                value=selected_month.strftime('%Y-%m'),
                label=selected_month.strftime('Tháng %m/%Y'),
                filename_suffix=selected_month.strftime('%Y_%m'),
            )

        if period == 'year':
            selected_year = datetime(year, 1, 1)
            return ReportPeriod(
                period='year',
                year=selected_year.year,
                month=None,
                day=None,
                value=selected_year.strftime('%Y'),
                label=selected_year.strftime('Năm %Y'),
                filename_suffix=selected_year.strftime('%Y'),
            )

        raise ValueError(f'Chế độ báo cáo không hợp lệ: {period}')

    def build_range_period(self, start_date=None, end_date=None):
        start = self._normalize_date(start_date) if start_date else None
        end = self._normalize_date(end_date) if end_date else None

        if start and end and start > end:
            raise ValueError('Ngày bắt đầu không được lớn hơn ngày kết thúc.')

        if start and end:
            label = f'Từ {self._format_filter_date(start)} đến {self._format_filter_date(end)}'
            suffix = f'{start.replace("-", "_")}_to_{end.replace("-", "_")}'
        elif start:
            label = f'Từ {self._format_filter_date(start)}'
            suffix = f'from_{start.replace("-", "_")}'
        elif end:
            label = f'Đến {self._format_filter_date(end)}'
            suffix = f'to_{end.replace("-", "_")}'
        else:
            raise ValueError('Vui lòng nhập ít nhất một ngày trong khoảng ngày tùy chọn.')

        return ReportPeriod(
            period='range',
            year=0,
            month=None,
            day=None,
            value=suffix,
            label=label,
            filename_suffix=suffix,
            start_date=start,
            end_date=end,
        )

    def apply_filters(self, period_context, payment_method=None, product_id=None, product_name=None, category=None):
        payment_method = self._clean_optional_filter(payment_method)
        product_name = self._clean_optional_filter(product_name)
        category = self._clean_optional_filter(category)
        parsed_product_id = int(product_id) if product_id not in (None, '', 'Tất cả') else None

        labels = [period_context.label]
        suffix_parts = [period_context.filename_suffix]

        if payment_method:
            labels.append(f'PTTT: {payment_method}')
            suffix_parts.append(f'pay_{self._safe_suffix(payment_method)}')
        if parsed_product_id:
            product_label = product_name or f'ID {parsed_product_id}'
            labels.append(f'Sản phẩm: {product_label}')
            suffix_parts.append(f'product_{parsed_product_id}')
        if category:
            labels.append(f'Danh mục: {category}')
            suffix_parts.append(f'cat_{self._safe_suffix(category)}')

        return ReportPeriod(
            period=period_context.period,
            year=period_context.year,
            month=period_context.month,
            day=period_context.day,
            value=period_context.value,
            label=' | '.join(labels),
            filename_suffix='_'.join(suffix_parts),
            start_date=period_context.start_date,
            end_date=period_context.end_date,
            payment_method=payment_method,
            product_id=parsed_product_id,
            product_name=product_name,
            category=category,
        )

    def get_period_filter(self, period_context, table_alias=None):
        column = 'transaction_date'
        if table_alias:
            column = f'{table_alias}.transaction_date'

        if period_context.period == 'day':
            return f'DATE({column}) = ?', (period_context.value,)
        if period_context.period == 'month':
            return f"strftime('%Y-%m', {column}) = ?", (period_context.value,)
        if period_context.period == 'year':
            return f"strftime('%Y', {column}) = ?", (period_context.value,)
        if period_context.period == 'range':
            clauses = []
            params = []
            if period_context.start_date:
                clauses.append(f'DATE({column}) >= ?')
                params.append(period_context.start_date)
            if period_context.end_date:
                clauses.append(f'DATE({column}) <= ?')
                params.append(period_context.end_date)
            return ' AND '.join(clauses) if clauses else '1=1', tuple(params)

        raise ValueError(f'Chế độ báo cáo không hợp lệ: {period_context.period}')

    def _normalize_date(self, value):
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').strftime('%Y-%m-%d')

    def _format_filter_date(self, value):
        return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')

    def _clean_optional_filter(self, value):
        value = (value or '').strip()
        if not value or value == 'Tất cả':
            return None
        return value

    def _safe_suffix(self, value):
        text = unicodedata.normalize('NFKD', str(value))
        text = text.encode('ascii', 'ignore').decode('ascii').lower()
        cleaned = ''.join(ch if ch.isalnum() else '_' for ch in text)
        return '_'.join(part for part in cleaned.split('_') if part) or 'filter'

    def _build_transaction_where(self, period_context, table_alias='t'):
        date_clause, date_params = self.get_period_filter(period_context, table_alias=table_alias)
        clauses = [date_clause]
        params = list(date_params)
        prefix = f'{table_alias}.'

        if period_context.payment_method:
            clauses.append(f"COALESCE(NULLIF({prefix}payment_method, ''), 'Không rõ') = ?")
            params.append(period_context.payment_method)

        if period_context.product_id or period_context.category:
            exists_clauses = [f'ti.transaction_id = {prefix}id']
            if period_context.product_id:
                exists_clauses.append('ti.product_id = ?')
                params.append(period_context.product_id)
            if period_context.category:
                exists_clauses.append('p.category = ?')
                params.append(period_context.category)
            clauses.append(
                '''
                EXISTS (
                    SELECT 1
                    FROM transaction_items ti
                    LEFT JOIN products p ON p.id = ti.product_id
                    WHERE ''' + ' AND '.join(exists_clauses) + '''
                )
                '''
            )

        return ' AND '.join(clauses), tuple(params)

    def _build_item_where(self, period_context):
        date_clause, date_params = self.get_period_filter(period_context, table_alias='t')
        clauses = [date_clause]
        params = list(date_params)

        if period_context.payment_method:
            clauses.append("COALESCE(NULLIF(t.payment_method, ''), 'Không rõ') = ?")
            params.append(period_context.payment_method)
        if period_context.product_id:
            clauses.append('ti.product_id = ?')
            params.append(period_context.product_id)
        if period_context.category:
            clauses.append('p.category = ?')
            params.append(period_context.category)

        return ' AND '.join(clauses), tuple(params)

    def get_summary(self, period_context):
        where_clause, params = self._build_transaction_where(period_context, table_alias='t')
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT
                COALESCE(SUM(t.total_amount), 0),
                COUNT(DISTINCT t.id),
                COALESCE(SUM(t.subtotal_amount), 0),
                COALESCE(SUM(t.discount_amount), 0),
                SUM(CASE WHEN t.refund_of IS NULL THEN 1 ELSE 0 END),
                COALESCE(SUM(CASE WHEN t.refund_of IS NULL THEN t.total_amount ELSE 0 END),0),
                COALESCE(SUM(CASE WHEN t.refund_of IS NOT NULL THEN -t.total_amount ELSE 0 END),0)
            FROM transactions t
            WHERE ''' + where_clause,
            params,
        )
        total_revenue, transaction_count, subtotal_revenue, total_discount, sale_count, sales_amount, refunded_amount = cursor.fetchone()

        item_where_clause, item_params = self._build_item_where(period_context)
        cursor.execute(
            '''
            SELECT COALESCE(SUM(ti.quantity), 0)
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            LEFT JOIN products p ON p.id = ti.product_id
            WHERE ''' + item_where_clause,
            item_params,
        )
        total_products_sold = cursor.fetchone()[0] or 0

        avg_per_transaction = (sales_amount / sale_count) if sale_count else 0
        return {
            'total_revenue': total_revenue or 0,
            'subtotal_revenue': subtotal_revenue or 0,
            'total_discount': total_discount or 0,
            'transaction_count': transaction_count or 0,
            'avg_per_transaction': avg_per_transaction,
            'total_products_sold': total_products_sold,
            'sale_count': sale_count or 0,
            'refund_count': transaction_count - (sale_count or 0),
            'refunded_amount': refunded_amount,
        }

    def get_daily_revenue(self, period_context):
        where, params = self._build_transaction_where(period_context, table_alias='t')
        rows = self.conn.execute(
            'SELECT substr(t.transaction_date,1,10), SUM(t.total_amount) FROM transactions t WHERE '
            + where + ' GROUP BY substr(t.transaction_date,1,10) ORDER BY 1 DESC LIMIT 14', params
        ).fetchall()
        return list(reversed(rows))

    def get_payment_breakdown(self, period_context):
        where_clause, params = self._build_transaction_where(period_context, table_alias='t')
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT
                COALESCE(NULLIF(t.payment_method, ''), 'Không rõ') AS method,
                COUNT(DISTINCT t.id) AS transaction_count,
                COALESCE(SUM(t.total_amount), 0) AS revenue
            FROM transactions t
            WHERE ''' + where_clause + '''
            GROUP BY COALESCE(NULLIF(t.payment_method, ''), 'Không rõ')
            ORDER BY revenue DESC
            ''',
            params,
        )
        return [
            {'method': method, 'transaction_count': count, 'revenue': revenue or 0}
            for method, count, revenue in cursor.fetchall()
        ]

    def get_top_products_by_quantity(self, period_context, limit=5):
        where_clause, params = self._build_item_where(period_context)
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT
                COALESCE(p.name, ti.product_name) AS product_name,
                COALESCE(SUM(ti.quantity), 0) AS total_quantity,
                COALESCE(SUM(ti.subtotal), 0) AS total_revenue
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            LEFT JOIN products p ON p.id = ti.product_id
            WHERE ''' + where_clause + '''
            GROUP BY COALESCE(p.name, ti.product_name)
            ORDER BY total_quantity DESC, total_revenue DESC
            LIMIT ?
            ''',
            params + (int(limit),),
        )
        return [
            {'product_name': name, 'quantity': quantity or 0, 'revenue': revenue or 0}
            for name, quantity, revenue in cursor.fetchall()
        ]

    def get_top_products_by_revenue(self, period_context, limit=5):
        where_clause, params = self._build_item_where(period_context)
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT
                COALESCE(p.name, ti.product_name) AS product_name,
                COALESCE(SUM(ti.quantity), 0) AS total_quantity,
                COALESCE(SUM(ti.subtotal), 0) AS total_revenue
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            LEFT JOIN products p ON p.id = ti.product_id
            WHERE ''' + where_clause + '''
            GROUP BY COALESCE(p.name, ti.product_name)
            ORDER BY total_revenue DESC, total_quantity DESC
            LIMIT ?
            ''',
            params + (int(limit),),
        )
        return [
            {'product_name': name, 'quantity': quantity or 0, 'revenue': revenue or 0}
            for name, quantity, revenue in cursor.fetchall()
        ]

    def get_transactions(self, period_context, limit=50):
        where_clause, params = self._build_transaction_where(period_context, table_alias='t')
        query = (
            '''
            SELECT
                t.id,
                t.transaction_date,
                t.subtotal_amount,
                t.discount_percent,
                t.discount_amount,
                t.total_amount,
                COALESCE(NULLIF(t.payment_method, ''), 'Không rõ') AS payment_method,
                t.refund_of, t.exchange_for, t.reason
            FROM transactions t
            WHERE ''' + where_clause + '''
            ORDER BY t.transaction_date DESC, t.id DESC
            '''
        )

        if limit is not None:
            query += ' LIMIT ?'
            params = params + (int(limit),)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [
            {
                'id': trans_id,
                'transaction_date': transaction_date,
                'subtotal_amount': subtotal_amount or 0,
                'discount_percent': discount_percent or 0,
                'discount_amount': discount_amount or 0,
                'total_amount': total_amount or 0,
                'payment_method': payment_method,
                'refund_of': refund_of,
                'exchange_for': exchange_for,
                'reason': reason or '',
            }
            for (
                trans_id,
                transaction_date,
                subtotal_amount,
                discount_percent,
                discount_amount,
                total_amount,
                payment_method,
                refund_of, exchange_for, reason,
            ) in cursor.fetchall()
        ]

    def get_low_stock_products(self, threshold=10, limit=50):
        return self.inventory_service.get_low_stock_products(threshold=threshold, limit=limit)

    def get_payment_methods(self):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT method
            FROM (
                SELECT DISTINCT COALESCE(NULLIF(payment_method, ''), 'Không rõ') AS method
                FROM transactions
            )
            ORDER BY method
            '''
        )
        return [row[0] for row in cursor.fetchall()]

    def get_product_filter_options(self):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT id, name, COALESCE(barcode, '')
            FROM products
            ORDER BY name ASC, id ASC
            '''
        )
        return [{'id': row[0], 'name': row[1], 'barcode': row[2]} for row in cursor.fetchall()]

    def get_category_filter_options(self):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT DISTINCT category
            FROM products
            WHERE category IS NOT NULL AND TRIM(category) != ''
            ORDER BY category
            '''
        )
        return [row[0] for row in cursor.fetchall()]

    def get_report_data(self, period_context, transaction_limit=None):
        return {
            'period': period_context,
            'generated_at': datetime.now(),
            'summary': self.get_summary(period_context),
            'payment_breakdown': self.get_payment_breakdown(period_context),
            'top_products_by_quantity': self.get_top_products_by_quantity(period_context),
            'top_products_by_revenue': self.get_top_products_by_revenue(period_context),
            'transactions': self.get_transactions(period_context, limit=transaction_limit),
            'low_stock_products': self.get_low_stock_products(),
        }


class TabularReportExporter:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else resolve_app_path('exports')

    def export_csv(self, report_data):
        """Export report data to a UTF-8 CSV file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        period_context = report_data['period']
        output_path = self.output_dir / f'revenue_report_{period_context.filename_suffix}.csv'

        with output_path.open('w', newline='', encoding='utf-8-sig') as csv_file:
            writer = csv.writer(csv_file)
            self._write_csv_sections(writer, report_data)

        return str(output_path.resolve())

    def export_excel(self, report_data):
        """Export report data to an XLSX file when openpyxl is installed."""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
        except ImportError as exc:
            raise RuntimeError('Chưa cài openpyxl. Hãy cài bằng: python -m pip install openpyxl') from exc

        self.output_dir.mkdir(parents=True, exist_ok=True)
        period_context = report_data['period']
        output_path = self.output_dir / f'revenue_report_{period_context.filename_suffix}.xlsx'

        workbook = Workbook()
        summary_sheet = workbook.active
        summary_sheet.title = 'Tong quan'
        self._write_excel_sheet(summary_sheet, self._summary_rows(report_data))

        payment_sheet = workbook.create_sheet('Thanh toan')
        self._write_excel_sheet(payment_sheet, self._payment_rows(report_data))

        top_quantity_sheet = workbook.create_sheet('Top so luong')
        self._write_excel_sheet(top_quantity_sheet, self._top_quantity_rows(report_data))

        top_revenue_sheet = workbook.create_sheet('Top doanh thu')
        self._write_excel_sheet(top_revenue_sheet, self._top_revenue_rows(report_data))

        transaction_sheet = workbook.create_sheet('Giao dich')
        self._write_excel_sheet(transaction_sheet, self._transaction_rows(report_data))

        for sheet in workbook.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.row == 1:
                        cell.font = Font(bold=True)
            for column_cells in sheet.columns:
                length = max(len(str(cell.value or '')) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 36)

        workbook.save(output_path)
        return str(output_path.resolve())

    def _write_csv_sections(self, writer, report_data):
        sections = [
            ('TỔNG QUAN', self._summary_rows(report_data)),
            ('DOANH THU THEO PHƯƠNG THỨC THANH TOÁN', self._payment_rows(report_data)),
            ('TOP SẢN PHẨM THEO SỐ LƯỢNG', self._top_quantity_rows(report_data)),
            ('TOP SẢN PHẨM THEO DOANH THU', self._top_revenue_rows(report_data)),
            ('DANH SÁCH GIAO DỊCH', self._transaction_rows(report_data)),
        ]

        for title, rows in sections:
            writer.writerow([title])
            writer.writerows(rows)
            writer.writerow([])

    def _write_excel_sheet(self, sheet, rows):
        for row in rows:
            sheet.append(row)

    def _summary_rows(self, report_data):
        summary = report_data['summary']
        return [
            ['Chỉ tiêu', 'Giá trị'],
            ['Kỳ báo cáo', report_data['period'].label],
            ['Ngày xuất', report_data['generated_at'].strftime('%d/%m/%Y %H:%M')],
            ['Tổng trước giảm', summary['subtotal_revenue']],
            ['Tổng giảm giá', summary['total_discount']],
            ['Tổng doanh thu sau giảm', summary['total_revenue']],
            ['Chứng từ bán + hoàn', summary['transaction_count']],
            ['Trung bình/đơn bán', summary['avg_per_transaction']],
            ['Tổng sản phẩm bán', summary['total_products_sold']],
        ]

    def _payment_rows(self, report_data):
        rows = [['Phương thức', 'Số giao dịch', 'Doanh thu']]
        rows.extend(
            [row['method'], row['transaction_count'], row['revenue']]
            for row in report_data['payment_breakdown']
        )
        return rows

    def _top_quantity_rows(self, report_data):
        rows = [['Sản phẩm', 'Số lượng', 'Doanh thu']]
        rows.extend(
            [row['product_name'], row['quantity'], row['revenue']]
            for row in report_data['top_products_by_quantity']
        )
        return rows

    def _top_revenue_rows(self, report_data):
        rows = [['Sản phẩm', 'Số lượng', 'Doanh thu']]
        rows.extend(
            [row['product_name'], row['quantity'], row['revenue']]
            for row in report_data['top_products_by_revenue']
        )
        return rows

    def _transaction_rows(self, report_data):
        rows = [['ID', 'Ngày giờ', 'Trước giảm', 'Giảm %', 'Giảm tiền', 'Thanh toán', 'PT thanh toán']]
        rows.extend(
            [
                row['id'],
                self._format_transaction_date(row['transaction_date']),
                row['subtotal_amount'],
                row['discount_percent'],
                row['discount_amount'],
                row['total_amount'],
                row['payment_method'],
            ]
            for row in report_data['transactions']
        )
        return rows

    def _format_transaction_date(self, value):
        try:
            return datetime.fromisoformat(str(value)).strftime('%d/%m/%Y %H:%M')
        except Exception:
            return str(value)


class RevenueReportExporter:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else resolve_app_path('reports')

    def export(self, report_data):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        period_context = report_data['period']
        output_path = self.output_dir / f'revenue_report_{period_context.filename_suffix}.pdf'

        try:
            self._write_pdf(output_path, report_data, use_unicode=True)
        except Exception as unicode_error:
            logger.exception("PDF export with Unicode font failed; retrying with ASCII fallback")
            self._write_pdf(
                output_path,
                report_data,
                use_unicode=False,
                fallback_reason=str(unicode_error),
            )

        return str(output_path.resolve())

    def _write_pdf(self, output_path, report_data, use_unicode=True, fallback_reason=None):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=12)
        font_family, bold_supported, unicode_enabled = self._configure_font(pdf, use_unicode)

        def safe_text(value):
            text = '' if value is None else str(value)
            if unicode_enabled:
                return text

            text = text.replace('₫', ' VND')
            normalized = unicodedata.normalize('NFKD', text)
            return normalized.encode('latin-1', 'ignore').decode('latin-1')

        def set_font(size=10, bold=False):
            style = 'B' if bold and bold_supported else ''
            pdf.set_font(font_family, style, size)

        def clipped(value, max_chars):
            text = safe_text(value)
            return text if len(text) <= max_chars else text[: max_chars - 3] + '...'

        def section(title):
            pdf.ln(4)
            set_font(12, bold=True)
            pdf.cell(0, 7, safe_text(title), ln=1)
            set_font(10)

        def key_value(label, value):
            set_font(10, bold=True)
            pdf.cell(55, 6, safe_text(label), border=0)
            set_font(10)
            pdf.cell(0, 6, safe_text(value), ln=1)

        def table(headers, rows, widths, aligns=None):
            aligns = aligns or ['L'] * len(headers)
            if not rows:
                set_font(10)
                pdf.cell(0, 6, safe_text('Không có dữ liệu'), ln=1)
                return

            set_font(9, bold=True)
            for header, width, align in zip(headers, widths, aligns):
                pdf.cell(width, 7, clipped(header, max(int(width / 2.2), 6)), border=1, align=align)
            pdf.ln()

            set_font(9)
            for row in rows:
                for value, width, align in zip(row, widths, aligns):
                    pdf.cell(width, 6, clipped(value, max(int(width / 2.2), 6)), border=1, align=align)
                pdf.ln()

        period_context = report_data['period']
        summary = report_data['summary']

        pdf.add_page()
        set_font(16, bold=True)
        pdf.cell(0, 9, safe_text('BÁO CÁO DOANH THU'), ln=1, align='C')
        set_font(11)
        pdf.cell(0, 7, safe_text('Cửa hàng: AnnaBeauty'), ln=1, align='C')
        pdf.ln(4)

        key_value('Kỳ báo cáo:', period_context.label)
        key_value('Ngày xuất:', report_data['generated_at'].strftime('%d/%m/%Y %H:%M'))
        if fallback_reason:
            key_value('Ghi chú font:', 'Đã fallback ASCII do lỗi font Unicode.')

        section('Tổng quan')
        key_value('Tổng trước giảm:', format_currency(summary['subtotal_revenue']))
        key_value('Tổng giảm giá:', format_currency(summary['total_discount']))
        key_value('Tổng doanh thu:', format_currency(summary['total_revenue']))
        key_value('Chứng từ bán + hoàn:', summary['transaction_count'])
        key_value('Trung bình/đơn bán:', format_currency(summary['avg_per_transaction']))
        key_value('Tổng sản phẩm đã bán:', summary['total_products_sold'])

        section('Doanh thu theo phương thức thanh toán')
        table(
            ['Phương thức', 'Số GD', 'Doanh thu'],
            [
                [row['method'], row['transaction_count'], format_currency(row['revenue'])]
                for row in report_data['payment_breakdown']
            ],
            [80, 30, 65],
            ['L', 'R', 'R'],
        )

        section('Danh sách giao dịch')
        table(
            ['ID', 'Ngày giờ', 'Trước giảm', 'Giảm', 'Thanh toán', 'PTTT'],
            [
                [
                    row['id'],
                    self._format_transaction_date(row['transaction_date']),
                    format_currency(row['subtotal_amount']),
                    format_currency(row['discount_amount']),
                    format_currency(row['total_amount']),
                    row['payment_method'],
                ]
                for row in report_data['transactions']
            ],
            [14, 38, 35, 28, 35, 30],
            ['R', 'L', 'R', 'R', 'R', 'L'],
        )

        pdf.output(str(output_path))

    def _configure_font(self, pdf, use_unicode):
        if not use_unicode:
            pdf.set_font('Arial', '', 10)
            return 'Arial', True, False

        regular_font, bold_font = self._find_unicode_fonts()
        if not regular_font:
            raise RuntimeError('Không tìm thấy font TTF Unicode để xuất PDF.')

        pdf.add_font('ReportFont', '', str(regular_font), uni=True)
        bold_supported = False
        if bold_font:
            try:
                pdf.add_font('ReportFont', 'B', str(bold_font), uni=True)
                bold_supported = True
            except Exception:
                bold_supported = False

        return 'ReportFont', bold_supported, True

    def _find_unicode_fonts(self):
        bundled_font_dir = resolve_bundle_path('fonts')
        regular_candidates = [
            bundled_font_dir / 'arial.ttf',
            bundled_font_dir / 'tahoma.ttf',
            bundled_font_dir / 'segoeui.ttf',
            resolve_app_path('fonts', 'arial.ttf'),
            resolve_app_path('fonts', 'tahoma.ttf'),
            resolve_app_path('fonts', 'segoeui.ttf'),
            Path('C:/Windows/Fonts/arial.ttf'),
            Path('C:/Windows/Fonts/tahoma.ttf'),
            Path('C:/Windows/Fonts/segoeui.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            Path('/Library/Fonts/Arial Unicode.ttf'),
        ]
        bold_candidates = [
            bundled_font_dir / 'arialbd.ttf',
            bundled_font_dir / 'tahomabd.ttf',
            bundled_font_dir / 'segoeuib.ttf',
            resolve_app_path('fonts', 'arialbd.ttf'),
            resolve_app_path('fonts', 'tahomabd.ttf'),
            resolve_app_path('fonts', 'segoeuib.ttf'),
            Path('C:/Windows/Fonts/arialbd.ttf'),
            Path('C:/Windows/Fonts/tahomabd.ttf'),
            Path('C:/Windows/Fonts/segoeuib.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ]

        regular_font = next((font for font in regular_candidates if font.exists()), None)
        bold_font = next((font for font in bold_candidates if font.exists()), None)
        return regular_font, bold_font

    def _format_transaction_date(self, value):
        try:
            return datetime.fromisoformat(str(value)).strftime('%d/%m/%Y %H:%M')
        except Exception:
            return str(value)
