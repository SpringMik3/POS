import os
from datetime import datetime
from modules.app_paths import resolve_app_path
from modules.app_logger import get_logger
from modules.utils import format_currency, format_datetime


logger = get_logger(__name__)


class ReceiptPrinter:
    def print_receipt_gdi(self, transaction_data, printer_name=None, font_name='Times New Roman', font_size=32):
        import win32print, win32ui
        import sys
        try:
            if printer_name is None:
                printer_name = win32print.GetDefaultPrinter()
            print(f"[LOG] Sử dụng máy in (GDI): {printer_name}", file=sys.stderr)
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hDC = win32ui.CreateDC()
                hDC.CreatePrinterDC(printer_name)
                hDC.StartDoc("Receipt")
                hDC.StartPage()
                # Tạo font Windows
                # Font thường
                font_normal = win32ui.CreateFont({
                    "name": font_name,
                    "height": font_size,
                    "weight": 400,
                })
                # Font đậm
                font_bold = win32ui.CreateFont({
                    "name": font_name,
                    "height": font_size,
                    "weight": 700,
                })
                # Font logo to và đậm
                font_logo = win32ui.CreateFont({
                    "name": font_name,
                    "height": font_size + 18,
                    "weight": 900,
                })
                # Nội dung hóa đơn
                # Khổ 80mm (khoảng 72mm in được) ~ 576px @203dpi
                width_px = 576
                x_center = width_px // 2
                y = 30
                line_height = font_size + 18
                # Logo AnnaBeauty
                hDC.SelectObject(font_logo)
                logo = "AnnaBeauty"
                hDC.TextOut(x_center - (len(logo)*font_size)//3, y, logo)
                y += font_size + 32
                # Địa chỉ, điện thoại
                hDC.SelectObject(font_normal)
                addr = "  Đông Cứu, Thượng Phúc, Hà Nội"
                phone = "DT: 0978880584"
                sohd = f"Số HD: {transaction_data['id']}"
                phone_sohd = f"{phone}   {sohd}"
                hDC.TextOut(x_center - (len(addr)*font_size)//4, y, addr)
                y += line_height
                hDC.SelectObject(font_bold)
                hDC.TextOut(x_center - (len(phone_sohd)*font_size)//4, y, phone_sohd)
                y += line_height
                hDC.SelectObject(font_normal)
                # Gạch ngang
                hDC.TextOut(x_center - 23*font_size//4, y, "-"*46)
                y += line_height
                ngay = f"Ngày: {transaction_data['datetime'].strftime('%d/%m/%Y ')}"
                hDC.TextOut(x_center - (len(ngay)*font_size)//4, y, ngay)
                y += line_height
                # Gạch ngang
                hDC.TextOut(x_center - 23*font_size//4, y, "-"*46)
                y += line_height
                # Sản phẩm: tên, số lượng, giá, thành tiền
                for item in transaction_data['items']:
                    # Khổ 80mm cho phép tên dài hơn
                    name = item['name'][:28]
                    qty = str(item['quantity'])
                    # Tên sản phẩm và số lượng căn giữa
                    sp_line = f"{name}   x{qty}"
                    hDC.TextOut(x_center - (len(sp_line)*font_size)//4, y, sp_line)
                    y += line_height
                    # Giá và thành tiền, có dấu gạch giữa
                    price = f"{int(item['price']):,}".replace(",", ".")
                    total = f"{int(item['subtotal']):,}".replace(",", ".")
                    price_line = f"{price} -------- {total}"
                    hDC.TextOut(x_center - (len(price_line)*font_size)//4, y, price_line)
                    y += line_height
                # Gạch ngang
                hDC.TextOut(x_center - 23*font_size//4, y, "-"*46)
                y += line_height

                # Tạm tính / Giảm giá / Tổng thanh toán
                subtotal = transaction_data.get('subtotal', transaction_data['total_amount'])
                discount_percent = transaction_data.get('discount_percent', 0)
                discount_amount = transaction_data.get('discount_amount', 0)
                total_after_discount = transaction_data.get('total_after_discount', transaction_data['total_amount'])

                hDC.SelectObject(font_normal)
                tam_tinh = f"Tạm tính: {int(subtotal):,} VND"
                hDC.TextOut(x_center - (len(tam_tinh)*font_size)//4, y, tam_tinh)
                y += line_height

                # Chỉ in dòng giảm giá nếu có
                if discount_percent and discount_percent > 0:
                    giam = f"Giảm {discount_percent:.0f}%: -{int(discount_amount):,} VND"
                    hDC.TextOut(x_center - (len(giam)*font_size)//4, y, giam)
                    y += line_height

                hDC.SelectObject(font_bold)
                tong = f"TỔNG: {int(total_after_discount):,} VND"
                hDC.TextOut(x_center - (len(tong)*font_size)//4, y, tong)
                y += line_height

                hDC.SelectObject(font_normal)
                pttt = f"PTTT: {transaction_data['payment_method']}"
                hDC.TextOut(x_center - (len(pttt)*font_size)//4, y, pttt)
                y += line_height
                # Gạch ngang
                hDC.TextOut(x_center - 16*font_size//4, y, "-"*32)
                y += line_height
                camon = "Cảm ơn quý khách!"
                hDC.SelectObject(font_bold)
                hDC.TextOut(x_center - (len(camon)*font_size)//4, y, camon)
                y += line_height
                hDC.SelectObject(font_normal)
                # Khoảng trắng cuối hóa đơn
                for _ in range(16):
                    y += line_height
                hDC.EndPage()
                hDC.EndDoc()
                hDC.DeleteDC()
                print("[LOG] Đã gửi hóa đơn qua GDI/win32ui", file=sys.stderr)
                return True, "Đã in hóa đơn qua GDI thành công"
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as e:
            logger.exception("Receipt printing failed")
            print(f"[LOG] Lỗi in GDI: {str(e)}", file=sys.stderr)
            return False, f"Lỗi in GDI: {str(e)}"
    
    def __init__(self):
        self.receipts_folder = str(resolve_app_path('receipts'))
        # Tạo thư mục receipts nếu chưa có
        if not os.path.exists(self.receipts_folder):
            os.makedirs(self.receipts_folder)
        
    
    def print_receipt(self, transaction_data, printer_name=None):
        return self.print_receipt_gdi(transaction_data, printer_name)
    
    def open_receipt_folder(self):
        """Mở thư mục chứa hóa đơn"""
        try:
            if os.path.exists(self.receipts_folder):
                os.startfile(self.receipts_folder)
        except Exception:
            logger.exception("Open receipt folder failed: %s", self.receipts_folder)
            pass
