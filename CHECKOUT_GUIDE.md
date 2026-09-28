# Thanh toán và giao hàng COD

Bản nâng cấp nằm trong mã nguồn Python. Các file EXE cũ trong `dist` và `release` chưa được đóng gói lại.

## Sử dụng

1. Chạy `pos_system.py`, thêm sản phẩm rồi chọn **THANH TOÁN**.
2. Nhập giảm giá 0–100%. Tổng thanh toán làm tròn đến đồng.
3. **Tiền mặt:** nhập tiền khách đưa; ứng dụng tính tiền thừa và chặn thanh toán thiếu tiền.
4. **Chuyển khoản:** nhập mã ngân hàng, số tài khoản, tên chủ tài khoản; chọn **Tạo / mở QR thanh toán**. Cấu hình được lưu vào SQLite để dùng lại. QR mở trong trình duyệt, cần Internet và gửi các thông tin này cùng số tiền/nội dung chuyển khoản đến VietQR. Đổi giảm giá phải tạo lại QR. Kiểm tra tên người nhận và số tiền trên ứng dụng ngân hàng trước khi chuyển.
5. **Thẻ / chuyển khoản:** nhân viên phải kiểm tra đã nhận tiền rồi đánh dấu xác nhận. Chưa có kết nối ngân hàng tự đối soát. QR không tự xác nhận thanh toán.
6. **COD:** nhập người nhận, điện thoại, địa chỉ, phí ship và thông tin vận chuyển. Lưu đơn sẽ trừ tồn kho để giữ hàng. Đây là đơn nội bộ, chưa gọi API tạo vận đơn của hãng vận chuyển.

## Theo dõi COD

Nút **ĐƠN GIAO HÀNG COD** nằm dưới nút thanh toán. Chọn đơn để xem địa chỉ/ghi chú, nhập mã vận đơn và cập nhật:

`Chờ giao → Đang giao → Đã giao → Đã thu COD`

Chỉ chọn **Đã thu COD** sau khi đã nhận đủ khoản thu hộ. Khi đó hệ thống tạo giao dịch doanh thu hàng hóa; phí ship là khoản thu hộ riêng, không cộng vào doanh thu hàng hóa. Tổng cần thu trên danh sách gồm tiền hàng sau giảm giá và phí ship.

Có thể hủy đơn ở bước **Chờ giao / Đang giao** khi đã nhận lại hàng. Thao tác hoàn tồn kho chỉ thực hiện một lần. Không hỗ trợ hoàn trả sau giao thành công trong luồng này.

## Kiểm chứng

Chạy `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
Nếu Python thiếu đường dẫn Tcl/Tk, dùng PowerShell:

```powershell
$env:TCL_LIBRARY = "$PWD\dist\pos_system\_internal\_tcl_data"
$env:TK_LIBRARY = "$PWD\dist\pos_system\_internal\_tk_data"
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kiểm thử dùng SQLite tạm, không ghi đơn thử vào dữ liệu cửa hàng. Chưa kiểm chứng chuyển tiền thực tế, quét bằng ứng dụng ngân hàng hoặc máy in vật lý.

Tham khảo định dạng QR: https://vietqr.io/danh-sach-api/link-tao-ma-nhanh/
