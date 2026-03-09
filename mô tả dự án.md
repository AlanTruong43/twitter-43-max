# Mô tả dự án: Twitter 43MAX Tool

## Mục đích
Cày view, tương tác (like + retweet) cho kênh chủ đích với nhiều phương thức khác nhau.

---

## Công nghệ & nền tảng
- Trình duyệt Chrome dựa theo **profile trong phần mềm Antidetect GenLogin**
- API GenLogin tham khảo trong file `Genlogin-API.postman_collection.json`
- Proxy HTTP định dạng: `host:port:user:pass` (mặc định luôn live, không cần xoay vòng)
- Extension Cloudflare / auto-click captcha đã được cài sẵn trong profile → tự động xử lý captcha, không cần can thiệp thêm

---

## Cấu trúc module

### 1. File code login (`login.py`)
- Login 100% theo **cookie**
  - Tool kiểm tra xem account đã có session (cookie đã lưu file) hay chưa.
  - Nếu chưa có, tool sử dụng cookie chuỗi ở cấu hình `account.txt` để inject trực tiếp thông qua lệnh JavaScript (`document.cookie = ...`).
  - Reload và kiểm tra trạng thái login. 
- Sau khi login thành công:
  - Lưu lại cookie phiên hiện tại để tái sử dụng
  - Ghi trạng thái account (`active` / `error` / `banned`) vào file `account_status.txt`

### 2. File code quản lý session / cookie (`session.py`)
- Kiểm tra cookie còn sống hay không trước khi dùng
- Nếu cookie hết hạn → tự động thực hiện login lại để làm mới session
- Lưu cookie mới sau mỗi phiên login thành công

### 3. File code tìm đến trang Twitter (`navigate.py`)
- **Tìm theo username**: truy cập thẳng vào trang `twitter.com/<username>`
- **Tìm theo hashtag**:
  - Tìm kiếm hashtag
  - Lướt ngẫu nhiên 5–10 tweet trong kết quả
  - Trong khi lướt, nếu phát hiện tweet có **username trùng với username cài đặt** → click vào username đó để vào trang target

### 4. File code tương tác (`interact.py`)
Sau khi vào trang username target:
- Lướt ngẫu nhiên **5–10 bài**
- Tương tác random theo tỉ lệ % đã cài đặt:
  - Like
  - Retweet
  - Follow
  - Unfollow
- Có **delay/sleep ngẫu nhiên** giữa mỗi hành động để tránh bị Twitter phát hiện bot

### 5. File cài đặt (`settings.py`)
Chỉnh trực tiếp trong file code, bao gồm:
- **Target**: username hoặc hashtag cần tương tác
- **Phương thức tìm**: theo `username` hoặc `hashtag`
- **Tỉ lệ % hành động**:
  - `LIKE_RATE` = x%
  - `RETWEET_RATE` = x%
  - `FOLLOW_RATE` = x%
  - `UNFOLLOW_RATE` = x%
- **Số luồng** (`MAX_THREADS`): số profile chạy đồng thời trong một lần
- **Delay**: khoảng thời gian sleep ngẫu nhiên giữa các hành động (min/max giây)

### 6. Danh sách tài khoản (`account.txt`)
Định dạng theo từng dòng:
```text
USERNAME|PASS|2FA|MAIL|PASSMAIL|COOKIE
```
*(Lưu ý: Tool hiện tại chỉ quan tâm 2 trường: `USERNAME` (để định danh match với GenLogin profile) và `COOKIE` (chuỗi cookie để đăng nhập). Các trường còn lại có thể là dữ liệu placeholder do không còn dùng).*

### 7. File code main (`main.py`)
- Đọc danh sách profile từ GenLogin API
- Đọc danh sách account từ `account.txt`
- Bỏ qua các account có trạng thái lỗi trong `account_status.txt`
- Chạy **đa luồng** theo số `MAX_THREADS` đã cài đặt
- Cơ chế ghép profile:
  - Tool tự động dò tìm tên Profile GenLogin có chứa `USERNAME` Twitter (hỗ trợ các hậu tố / stt, ví dụ username `AlanC`, profile tên `AlanC_001` sẽ được tự động match chuẩn).
  - Không mở đè 1 profile cho 2 account.
- Mỗi luồng thực hiện tuần tự:
  1. Mở profile GenLogin tương ứng
  2. Kết nối ChromeDriver và inject Cookie (nếu chưa có session cache)
  3. Kiểm tra thành công login
  4. Tìm đến trang target (theo username hoặc hashtag)
  5. Tương tác ngẫu nhiên theo cài đặt
  6. Đóng profile

---

## Quy trình hoạt động

1. **Chuẩn bị**:
   - Tạo sẵn các cấu hình Profile trong group Twitter trên phần mềm GenLogin (Có thể tạo hàng loạt).
   - Thiết lập Proxy cho các profile ngay từ phần mềm GenLogin.
   - Cài đặt tính năng/extension bypass Captcha cho profile nếu cần.
   - Quan trọng: **Phải chứa Username Twitter trong tên Profile** (ví dụ `UserABC_001`) để tool ghép chuẩn xác.
2. **Cài đặt**: chỉnh các thông số trong `settings.py` (group name, tỷ lệ hành động, delay...).
3. **Chạy tool** (`main.py`):
   - Đọc danh sách account, bỏ qua acc lỗi
   - Dò và ghép cặp (Account - GenLogin Profile).
   - Mở đồng thời `MAX_THREADS` profile
   - Mỗi profile: login bằng cookie → tìm target → lướt ngẫu nhiên → tương tác (like, rt) → đóng browser.
   - Vòng lặp (`LOOP_COUNT`): Mở lại profile sau khi nghỉ để cày tiếp nếu cài đặt số vòng lớn hơn 1.
   - Tiếp tục cho đến hết danh sách
4. **Xử lý lỗi**:
   - Ghi lỗi chi tiết + trạng thái account vào `error.txt` và `account_status.txt`
   - **Tự động ngắt vòng lặp**: Profile nào phát sinh lỗi trong quá trình chạy sẽ dừng lại ngay lập tức và chuyển sang account tiếp theo, không lặp lại (`LOOP_COUNT` bị hủy bỏ cho profile đó).

---

## 8. Kiểm tra lỗi phát sinh
- Nếu lỗi phát sinh thì ghi vào file `error.txt` để fix dần
- Account gặp lỗi (sai pass, 2FA, suspend, ...) → ghi trạng thái vào `account_status.txt`
- Các lần chạy tiếp theo tự động **bỏ qua** account đã có trạng thái lỗi, tránh mất thời gian