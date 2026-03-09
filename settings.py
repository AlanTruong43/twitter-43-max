# ============================================================
#  TWITTER 43MAX – CÀI ĐẶT
#  Chỉnh sửa các thông số bên dưới trước khi chạy
# ============================================================

# ---- GenLogin API ----
GENLOGIN_API_URL  = "http://127.0.0.1:55550"   # URL local của GenLogin app
GENLOGIN_EMAIL    = "cipher43"
GENLOGIN_PASSWORD = "Alantruong@113"
GENLOGIN_GROUP    = "twitter"                   # Tên group chứa profile Twitter

# ---- Target ----
# Chọn "username" hoặc "hashtag"
TARGET_MODE     = "username"

# Nếu TARGET_MODE = "username": truy cập thẳng trang profile này
TARGET_USERNAME = "alancipher43"

# Nếu TARGET_MODE = "hashtag": tìm hashtag, dò tweet của TARGET_USERNAME
TARGET_HASHTAG  = "Bitcoin"

# ---- Tỉ lệ tương tác (0–100) ----
LIKE_RATE     = 30   # % bài sẽ được like
RETWEET_RATE  = 5   # % bài sẽ được retweet

# ---- Số tweet lướt trên trang target (ngẫu nhiên trong khoảng) ----
SCROLL_MIN = 5
SCROLL_MAX = 10

# ---- Delay giữa các hành động (giây) ----
DELAY_MIN = 1   # giây
DELAY_MAX = 2   # giây

# ---- Cấu hình lặp lại ----
LOOP_COUNT = 5    # Số lần lặp lại kịch bản cho mỗi account (sau khi đóng sẽ mở lại)

# ---- Đa luồng ----
MAX_THREADS = 5   # Số profile chạy đồng thời


# ---- File paths ----
ACCOUNT_FILE        = "account.txt"
ACCOUNT_STATUS_FILE = "account_status.txt"
ERROR_LOG_FILE      = "error.txt"
COOKIE_DIR          = "cookies"

