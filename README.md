# AnnaBeauty POS

Ứng dụng quản lý bán hàng trên Windows, viết bằng Python và Tkinter, lưu dữ liệu bằng SQLite.

## Chức năng

- Quản lý sản phẩm, tồn kho và bán hàng bằng mã vạch.
- Thanh toán, quản lý khách hàng, đơn giao hàng và COD.
- Xử lý trả hàng, báo cáo doanh thu và xuất dữ liệu.
- In hóa đơn trên Windows và sao lưu cơ sở dữ liệu.

## Chạy từ mã nguồn

Cài Python có Tkinter trên Windows, sau đó chạy trong thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe pos_system.py
```

Ứng dụng tự tạo cơ sở dữ liệu khi chưa có. Dữ liệu cục bộ nằm trong `pos_database.db`; các thư mục `backups`, `exports`, `receipts`, `reports` và `logs` chứa dữ liệu phát sinh và không được đưa vào Git.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Đóng gói Windows

Sau khi kích hoạt môi trường Python đã cài dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
.\build_exe.ps1 -Version 2.1.0
```

Bản đóng gói nằm trong `release/AnnaBeauty_POS_v2.1.0/`. Giữ nguyên cả thư mục khi chạy chương trình. Script build sao chép cơ sở dữ liệu hiện có vào bản đóng gói; hãy dùng dữ liệu trống hoặc dữ liệu mẫu nếu phân phối bản này.

## Tài liệu

- [Thanh toán](CHECKOUT_GUIDE.md)
- [Khách hàng, trả hàng và COD](CUSTOMERS_RETURNS_COD_GUIDE.md)
- [Giao diện làm việc](WORKSPACE_UI_GUIDE.md)
