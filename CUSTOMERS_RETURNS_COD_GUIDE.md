# Khách hàng, đổi trả và COD

Ứng dụng mở lên dùng ngay, không có tài khoản hoặc phân quyền mới. Chạy `pos_system.py`; các EXE cũ chưa được đóng gói lại.

## Khách hàng

Vào **KHÁCH HÀNG & ĐỔI TRẢ → Khách hàng** để thêm, sửa, tìm theo tên/điện thoại và xem lịch sử. Điện thoại có thể để trống; nếu nhập thì không trùng khách khác. Khi thanh toán, chọn khách hoặc giữ **Khách lẻ**. Nút thêm khách có ngay trong cửa sổ thanh toán. Chọn khách sẽ điền tên, điện thoại và địa chỉ giao COD; có thể sửa người nhận riêng cho từng đơn.

Số mua ròng là doanh thu giao dịch trừ tiền hoàn. Đơn COD chỉ tính vào số này sau khi xác nhận Đã thu COD. Lịch sử hiển thị riêng giao dịch và đơn vận chuyển để tra cứu, không cộng hai dòng đó lần nữa. Đơn cũ không có khách vẫn giữ là khách lẻ; không tự ghép bằng tên.

## Đổi trả, hoàn tiền và hủy giao dịch đã thanh toán

1. Vào **Đổi trả / Hoàn tiền**, tìm và chọn đơn gốc rồi mở **Tạo phiếu đổi trả**.
2. Chọn dòng sản phẩm, nhập số lượng và bấm **Áp dụng dòng**. Hoặc chọn **Trả toàn bộ phần còn lại** để hoàn/hủy toàn bộ đơn. Muốn bỏ một dòng khỏi phiếu, chọn **Bỏ dòng**.
3. Chỉ bật **Nhập lại kho** nếu đã nhận hàng và hàng còn bán được. Hàng hỏng hoặc mất thì bỏ chọn trước khi áp dụng dòng. Với đơn chưa giao, hàng vẫn còn tại cửa hàng và được nhập lại số tồn đã trừ lúc bán.
4. Chọn phương thức hoàn thực tế, nhập lý do, kiểm tra số tiền, thực hiện hoàn tiền cho khách rồi xác nhận lưu. Ứng dụng ghi nhận sổ sách, không tự chuyển tiền qua ngân hàng.

Tiền hoàn dựa trên số tiền sau giảm của đơn gốc, được phân bổ đến đơn vị đồng. Trả nhiều lần không vượt số lượng mua; tổng các lần hoàn toàn bộ bằng số tiền đơn gốc. Đơn gốc không bị xóa. Phiếu hoàn ghi số âm trong báo cáo và trang thuế vào ngày hoàn, không sửa kỳ bán cũ. Có lịch sử phiếu hoàn ngay trong cửa sổ đổi trả.

**Đổi sang sản phẩm khác:** chọn **Hoàn & lập đơn đổi** tại trang chính. Giỏ hàng phải trống trước thao tác này. Sau khi hoàn đơn cũ, ứng dụng chuyển sang bán hàng để chọn sản phẩm mới, tự liên kết đơn gốc và khách hàng. Tiền hoàn và thanh toán đơn mới là hai thao tác riêng; phần mềm không tự bù trừ hai khoản. Có thể bỏ chọn liên kết trong cửa sổ thanh toán nếu đổi ý. Đơn đổi mới thanh toán ngay, không dùng COD.

## COD

Tạo đơn COD như cũ tại thanh toán. Kiểm tra và xử lý tại trang **ĐƠN COD** trên thanh điều hướng chính: tìm đơn, lọc trạng thái, xem chi tiết, cập nhật giao hàng và đối soát. Trang này mở trực tiếp, không cần có giỏ hàng hoặc mở thanh toán. Danh sách tự tải lại khi chuyển sang trang; bộ lọc đang chọn được giữ lại.

- Chờ giao → Đang giao hoặc Đã hủy. Hủy trước khi giao trả lại hàng đã giữ.
- Đang giao → Đã giao hoặc Giao thất bại.
- Giao thất bại → Đang giao (giao lại) hoặc Chờ hoàn hàng.
- Đã giao → Đã thu COD hoặc Chờ hoàn hàng (khách trả trước đối soát).
- Chờ hoàn hàng → Đã hoàn hàng. Chỉ bước này mới hoàn tồn kho nếu đã xác nhận hàng còn bán được. Hàng hỏng/mất có thể kết thúc mà không cộng tồn.

Các bước hủy/thất bại/hoàn phải có lý do. Đã thu COD/Đã hoàn hàng/Đã hủy là trạng thái kết thúc, không xử lý tiền hoặc tồn kho lần hai. Sau khi đã thu COD, khách trả hàng bằng phiếu hoàn của giao dịch được ghi ở chi tiết đơn.

Khi đối soát, nhập **phí hãng khấu trừ** và **tiền thực chuyển về**. Dự kiến nhận = tiền hàng + ship khách trả − phí hãng. Nếu tiền thực nhận khác dự kiến, bắt buộc ghi chú chênh lệch. Doanh thu hàng hóa vẫn theo tiền hàng của đơn; phí và chênh lệch lưu riêng ở hồ sơ COD, không dùng tiền chuyển ròng để thay doanh thu và không tự ghi thêm thu/chi.

Nút **Chỉ lưu vận đơn / ghi chú** cho phép cập nhật hãng giao, vận đơn và ghi chú mà không chuyển trạng thái. Lịch sử xử lý lưu tại từng đơn. Các tổng ở đầu trang COD là số hiện tại của mọi kỳ; chênh lệch có thể bù trừ giữa các đơn, cần xem chi tiết để đối chiếu.

Không tự gọi API hãng vận chuyển hoặc ngân hàng. Những đơn đã thu COD từ phiên bản cũ vẫn giữ nguyên; nếu chưa có số liệu phí/thực nhận, không được coi là đã đối soát chi tiết.

## Dữ liệu và kiểm thử

Lần đầu nâng cấp dữ liệu cũ, ứng dụng sao lưu trước khi thêm các bảng/cột mới. Không thực hiện thao tác đổi trả hoặc giao hàng thử trên dữ liệu bán thật.

Các kiểm thử dùng database tạm: khách trùng số điện thoại, đổi trả nhiều lần và làm tròn, hỏng hàng, rollback khi không hoàn được kho, liên kết đơn đổi, COD thất bại/hoàn, đối soát lệch tiền, xử lý lặp và khởi tạo các hộp thoại thật.
