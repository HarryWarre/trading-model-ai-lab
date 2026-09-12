# Research 041 — phản ứng sau thông báo FOMC trên 15 tài sản

## Quyết định

**Bác bỏ giả thuyết; research-only.** Cả quy tắc chỉ dùng giá và mô hình tuyến tính nhiều đầu vào đều âm sau chi phí 4 pip. Mô hình nhiều đầu vào ít âm hơn, nhưng không chứng minh được lợi thế.

## Cơ chế kinh tế

Một thông báo của ngân hàng trung ương đưa thông tin mới ra thị trường. Nghiên cứu của Andersen, Bollerslev, Diebold và Vega cho thấy giá và biến động thường tập trung quanh thời điểm các tin kinh tế được công bố: https://doi.org/10.1257/000282803321455151. Nghiên cứu này kiểm tra một câu hỏi cụ thể: nếu biết hướng biến động trong 5 phút đầu sau thông báo, hướng đó có tiếp tục đúng trong 55 phút sau không?

## Giả thuyết và mô hình đã đăng ký

Với mỗi tài sản `i` và cuộc họp `e`:

- `r0(i,e)`: log-return từ thời điểm công bố đến 5 phút sau;
- `r1(i,e)`: log-return từ phút 5 đến phút 60;
- quy tắc giá: giao dịch theo `sign(r0)`;
- mô hình nhiều đầu vào: dự báo `r1` bằng ridge mở rộng với ba đầu vào `[1, r0 / volatility_20_day, VIX_lagged]`, chỉ học từ các cuộc họp trước đó;
- trọng số chính là nghịch đảo biến động trước sự kiện; có thêm baseline chia đều;
- nếu giá bị thiếu hoặc quá cũ hơn 10 phút thì bỏ tài sản đó, không điền giá;
- phí CFD cố định là 4 pip cho một vòng mua-bán; kiểm tra 0x, 1x, 2x và 4x.

Các cổng đạt đã đăng ký trước: lợi nhuận 1x dương; mô hình nhiều đầu vào thắng quy tắc giá; xác suất bootstrap lợi nhuận dương ít nhất 95%; dương ở hai nửa mẫu; ít nhất 3/4 nhóm tài sản dương; vẫn dương ở 2x phí.

## Dữ liệu và kiểm soát lỗi

- Panel 5 phút UTC năm 2024 có 15 cột tài sản, nhưng BCOUSD không có quan sát hợp lệ quanh 7 sự kiện; vì vậy mẫu chạy thực tế là 14/15 tài sản.
- Có 8 thời điểm FOMC chính thức từ Federal Reserve, nhưng một sự kiện không có đủ quan sát hợp lệ trong cửa sổ 60 phút nên kết quả dùng 7 sự kiện.
- Panel hiện tại có SHA-256 `e632e54adb79e027e991bb335a917e9a7a30e16c6ddf33b0daecc9ceeae5d05c`.
- File thời điểm FOMC có SHA-256 `991875afeea3029cd8a9d812685577d39c51220ef76c9cbd62bd454a5c22a552`.
- File VIX có SHA-256 `d189972fce09597c45f246711881ba8ab35acca9ad52b98027214c42bb01422c`.
- Việc dùng dữ liệu sau thông báo chỉ bắt đầu từ phút thứ 5; không dùng giá tương lai để tạo tín hiệu.

## Kết quả

| Mô hình | Phí | Lợi nhuận | Số vòng mua-bán | Xác suất bootstrap mean > 0 |
|---|---:|---:|---:|---:|
| Giá, nghịch đảo biến động | 0x | −0,110% | 88 | 5,02% |
| Giá, nghịch đảo biến động | 1x | −0,328% | 88 | 0,00% |
| Giá, nghịch đảo biến động | 2x | −0,546% | 88 | 0,00% |
| Giá, nghịch đảo biến động | 4x | −0,980% | 88 | 0,00% |
| Ridge mở rộng | 0x | −0,035% | 97 | 33,65% |
| Ridge mở rộng | 1x | −0,246% | 97 | 0,97% |
| Ridge mở rộng | 2x | −0,456% | 97 | 0,00% |
| Ridge mở rộng | 4x | −0,874% | 97 | 0,00% |

Baseline chia đều với quy tắc giá đạt `−0,341%` ở 1x. Bỏ từng nhóm tài sản với quy tắc giá vẫn âm: bỏ năng lượng `−0,328%`, bỏ cổ phiếu `−0,312%`, bỏ FX `−0,035%`, bỏ kim loại `−0,309%`.

## Kết luận dễ hiểu

Mô hình phức tạp hơn đã đỡ tệ hơn mô hình chỉ nhìn giá, nhưng vẫn mất tiền. Nghĩa là vấn đề không chỉ là “thêm vài dữ liệu rồi dùng mô hình thông minh hơn”. Tín hiệu 5 phút đầu sau tin không tiếp tục đủ ổn định trong 55 phút tiếp theo, và phí 4 pip làm kết quả xấu thêm.

Nghiên cứu không đạt bất kỳ tiêu chuẩn nào để gọi là alpha hay dùng thật. Mẫu còn nhỏ, năm 2024 đã được dùng trước đó, và chưa có holdout 2025–2026. Không được tối ưu lại sau khi thấy kết quả.

## Việc tiếp theo

1. Hoàn tất panel 2023–2025 đã có 45 archive nhưng chưa ghép thành tệp chạy được.
2. Chỉ thêm ECB/BoE khi lấy được giờ công bố lịch sử có nguồn chính thức rõ ràng; không tự đoán giờ.
3. Tìm dữ liệu dự báo kinh tế có dấu thời gian phát hành và dữ liệu thực tế point-in-time. Nếu không có, chỉ chạy event-timing study và không gọi đó là surprise model.

