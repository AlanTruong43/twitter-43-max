"""
session.py
Quản lý cookie / session cho từng tài khoản Twitter.
"""

import os
import time
import json
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from settings import COOKIE_DIR

logger = logging.getLogger(__name__)

os.makedirs(COOKIE_DIR, exist_ok=True)


# ------------------------------------------------------------------ #
#  Parse account line
# ------------------------------------------------------------------ #
def parse_account(line: str) -> dict:
    """
    Phân tích dòng account theo định dạng:
    USERNAME|PASS|2FA|MAIL|PASSMAIL|COOKIE(optional)
    Trả về dict các trường.
    """
    parts = line.strip().split("|", 5)
    if len(parts) < 5:
        raise ValueError(f"Dòng account không hợp lệ: {line!r}")
    return {
        "username": parts[0],
        "password": parts[1],
        "totp_secret": parts[2],          # secret key 2FA (TOTP), hoặc rỗng
        "email": parts[3],
        "passmail": parts[4],
        "cookie": parts[5] if len(parts) > 5 else "",
    }


# ------------------------------------------------------------------ #
#  Cookie helpers
# ------------------------------------------------------------------ #
def _cookie_file(username: str) -> str:
    return os.path.join(COOKIE_DIR, f"{username}.json")


def inject_raw_cookie_string(driver: WebDriver, cookie_str: str):
    """
    Inject cookie dạng chuỗi (key=value; key2=value2 ...) vào driver dùng Selenium add_cookie.
    """
    if not cookie_str:
        return
        
    driver.get("https://x.com")
    time.sleep(2)
    driver.delete_all_cookies()
    
    pairs = cookie_str.split(';')
    added_count = 0
    
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        if '=' not in pair:
            continue
            
        eq_idx = pair.index('=')
        name = pair[:eq_idx].strip()
        value = pair[eq_idx+1:].strip()
        
        cookie_dict = {
            'name': name,
            'value': value,
            'domain': '.x.com',
            'path': '/',
            'secure': True
        }
        try:
            driver.add_cookie(cookie_dict)
            added_count += 1
        except Exception as e:
            logger.debug(f"Không thể add cookie {name}: {e}")
            
    logger.info(f"Đã nạp {added_count} cookie qua Selenium add_cookie.")
    
    driver.refresh()
    time.sleep(3)
    
    driver.get("https://x.com/home")
    time.sleep(5)
    logger.info(f"URL sau khi inject: {driver.current_url} | Title: {driver.title}")

def save_cookies(driver: WebDriver, username: str):
    """Lưu toàn bộ cookie hiện tại ra file JSON."""
    cookies = driver.get_cookies()
    path = _cookie_file(username)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    logger.info(f"Đã lưu {len(cookies)} cookie → {path}")


def load_cookies_from_file(driver: WebDriver, username: str) -> bool:
    """
    Load cookie từ file JSON đã lưu và inject vào driver.
    Trả về True nếu load được, False nếu file không tồn tại.
    """
    path = _cookie_file(username)
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    driver.get("https://x.com")
    for cookie in cookies:
        try:
            # Bỏ các field selenium không chấp nhận
            for key in ("expiry", "sameSite"):
                cookie.pop(key, None)
            driver.add_cookie(cookie)
        except Exception as e:
            logger.debug(f"Skip cookie {cookie.get('name')}: {e}")
    logger.info(f"Load {len(cookies)} cookie từ file cho @{username}")
    return True


# ------------------------------------------------------------------ #
#  Kiểm tra đã login chưa
# ------------------------------------------------------------------ #
def is_logged_in(driver: WebDriver, navigate: bool = True) -> bool:
    """
    Kiểm tra xem đã đăng nhập Twitter chưa.
    navigate=False: không navigate thêm, chỉ check URL + DOM hiện tại.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    try:
        if navigate:
            driver.get("https://x.com/home")
            time.sleep(5)

        current = driver.current_url
        logger.info(f"is_logged_in checking URL: {current}")
        
        # Nếu bị redirect về login page → chưa login
        if "/login" in current or "i/flow" in current or "/logout" in current:
            return False
            
        # Kiểm tra sidebar nav tồn tại là dấu hiệu vào feed thành công
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//nav[@aria-label="Primary navigation"]'))
        )
        return True
    except Exception as e:
        logger.warning(f"is_logged_in không tìm thấy Feed Navigation: {e}")
        return False
