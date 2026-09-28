# Giao diện thống kê, sản phẩm và hỗ trợ khai thuế

Chạy mã nguồn bằng `pos_system.py`. Các bản EXE đã đóng gói trước đây chưa chứa thay đổi này.

- **Thống kê:** bộ lọc ngày/tháng/năm và khoảng ngày; tab Tổng quan có chỉ số và biểu đồ 14 ngày có giao dịch gần nhất trong bộ lọc; tab Lịch sử hiển thị 50 giao dịch gần nhất. Các nút xuất báo cáo vẫn xuất toàn bộ giao dịch trong bộ lọc.
- **Sản phẩm:** danh sách bên trái, biểu mẫu bên phải. Chọn một dòng để sửa; Làm mới xóa biểu mẫu để thêm mới. Lọc theo tên/mã vạch, danh mục hoặc tồn kho. Màu đỏ là hết hàng, màu cam là còn 1–10 đơn vị. Số sản phẩm và đơn vị trên đầu trang phản ánh bộ lọc đang dùng. Tồn kho là số đang có thể bán, đã trừ hàng giữ cho COD.
- **Hỗ trợ khai thuế:** nhập và lưu hồ sơ người nộp thuế, chọn kỳ và tổng hợp. Bản đối chiếu HTML có hồ sơ, doanh thu trước/sau giảm, ghi chú và toàn bộ giao dịch trong kỳ. Mở file bằng trình duyệt và chọn In để lưu PDF. Ghi chú chỉ được đưa vào bản xuất, không tự lưu khi đóng ứng dụng.

Trang thuế hỗ trợ chuẩn bị và đối chiếu số liệu, chưa lập/nộp tờ khai theo mẫu pháp định và không tính thuế phải nộp. Dữ liệu doanh thu dùng ngày giao dịch đang lưu trong POS. COD được ghi nhận khi Đã thu COD; phí ship không được cộng vào doanh thu. Mục COD chưa thu là tình trạng hiện tại của mọi kỳ, không phải số dư lịch sử tại ngày kết thúc kỳ. Cần đối chiếu hóa đơn, thời điểm ghi nhận, hoàn trả và doanh thu ngoài POS trước khi kê khai.

Các trang tự tải lại dữ liệu khi chuyển tab. Những chức năng thanh toán, QR, quản lý đơn COD và xuất báo cáo cũ vẫn được giữ lại.
