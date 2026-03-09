"""
login.py
Xử lý đăng nhập Twitter:
  - Ưu tiên login bằng cookie (nhanh, tránh lock)
  - Fallback: login email + pass + 2FA (qua UnlimitMail)
"""

import time
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from session import (
    parse_account,
    inject_raw_cookie_string,
    load_cookies_from_file,
    save_cookies,
    is_logged_in,
)
from account_status import mark_error, mark_active

logger = logging.getLogger(__name__)

TWITTER_LOGIN_URL = "https://x.com/i/flow/login"


# ------------------------------------------------------------------ #
#  Helper: chờ và click element
# ------------------------------------------------------------------ #
def _wait_click(driver, xpath, timeout=20):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    el.click()
    return el


def _wait_type(driver, xpath, text, timeout=20):
    el = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    el.clear()
    for ch in text:          # gõ từng ký tự giống người dùng thật
        el.send_keys(ch)
        time.sleep(0.05)
    return el


# ------------------------------------------------------------------ #
#  Login bằng cookie chuỗi (từ account.txt)
# ------------------------------------------------------------------ #
def _try_cookie_string(driver: WebDriver, account: dict) -> bool:
    if not account.get("cookie"):
        return False
    logger.info(f"[{account['username']}] Thử inject cookie chuỗi...")
    inject_raw_cookie_string(driver, account["cookie"])
    # inject_raw_cookie_string đã navigate tới /home và chờ 5s
    if is_logged_in(driver, navigate=False):
        logger.info(f"[{account['username']}] Login bằng cookie chuỗi OK")
        save_cookies(driver, account["username"])
        return True
    return False


# ------------------------------------------------------------------ #
#  Login bằng cookie file (đã lưu từ lần trước)
# ------------------------------------------------------------------ #
def _try_cookie_file(driver: WebDriver, account: dict) -> bool:
    logger.info(f"[{account['username']}] Thử load cookie file...")
    if load_cookies_from_file(driver, account["username"]):
        driver.refresh()
        time.sleep(3)
        if is_logged_in(driver):
            logger.info(f"[{account['username']}] Login bằng cookie file OK")
            return True
    return False


# ------------------------------------------------------------------ #
#  Hàm main: login cho 1 tài khoản
# ------------------------------------------------------------------ #
def login(driver: WebDriver, account: dict) -> bool:
    """
    Thử đăng nhập chỉ bằng cookie theo thứ tự:
    1. Cookie file (session đã lưu trước)
    2. Cookie chuỗi từ account.txt
    Trả về True nếu login thành công. Nếu thất bại, đánh dấu error.
    """
    username = account["username"]

    if _try_cookie_file(driver, account):
        mark_active(username)
        return True

    if _try_cookie_string(driver, account):
        mark_active(username)
        return True

    # Không sử dụng username/password/2FA nữa
    mark_error(username, "die_cookie")
    logger.error(f"[{username}] Đăng nhập thất bại: Cookie đã chết hoặc không hợp lệ")
    return False

