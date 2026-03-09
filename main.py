"""
main.py
Orchestrator chính của Twitter 43MAX Tool.
Đọc danh sách profile GenLogin → chạy đa luồng → mỗi luồng login + navigate + interact.
"""

import os
import time
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from settings import (
    ACCOUNT_FILE,
    ERROR_LOG_FILE,
    MAX_THREADS,
    LOOP_COUNT,
)
from genlogin_api import GenLoginAPI
from session import parse_account
from account_status import is_skippable, mark_error
from login import login
from navigate import navigate_to_target
from interact import interact_with_feed

# ------------------------------------------------------------------ #
#  Logging setup
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("tool.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


# ------------------------------------------------------------------ #
#  Ghi lỗi ra file
# ------------------------------------------------------------------ #
def _log_error(username: str, msg: str):
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {username}: {msg}\n")


# ------------------------------------------------------------------ #
#  Đọc danh sách account
# ------------------------------------------------------------------ #
def load_accounts() -> list:
    if not os.path.exists(ACCOUNT_FILE):
        logger.error(f"Không tìm thấy {ACCOUNT_FILE}")
        return []
    accounts = []
    with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                acc = parse_account(line)
                if is_skippable(acc["username"]):
                    logger.info(f"[{acc['username']}] Đã có lỗi trước → bỏ qua")
                    continue
                accounts.append(acc)
            except Exception as e:
                logger.warning(f"Dòng account không hợp lệ: {line!r} – {e}")
    return accounts


# ChromeDriver path cache (tải 1 lần, tái dùng)
_CHROMEDRIVER_PATH = None

def _get_chromedriver_path() -> str:
    """Tải ChromeDriver phù hợp với Chrome version của GenLogin (143)."""
    global _CHROMEDRIVER_PATH
    if _CHROMEDRIVER_PATH:
        return _CHROMEDRIVER_PATH
    try:
        # Tự động tải đúng version dựa theo phiên bản Chrome của hệ thống GenLogin
        _CHROMEDRIVER_PATH = ChromeDriverManager(driver_version="143.0.7499.71").install()
        logger.info(f"ChromeDriver path: {_CHROMEDRIVER_PATH}")
    except Exception as e:
        logger.warning(f"Không tải được ChromeDriver 143: {e} — dùng Selenium Manager mặc định")
        _CHROMEDRIVER_PATH = None   # Selenium sẽ tự tìm
    return _CHROMEDRIVER_PATH


def _connect_driver(debug_port: int) -> webdriver.Chrome:
    """Kết nối ChromeDriver tới profile GenLogin đang mở qua remote debugging."""
    chrome_opts = Options()
    chrome_opts.add_experimental_option(
        "debuggerAddress", f"127.0.0.1:{debug_port}"
    )
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")

    cd_path = _get_chromedriver_path()
    if cd_path:
        service = Service(executable_path=cd_path)
        driver = webdriver.Chrome(service=service, options=chrome_opts)
    else:
        driver = webdriver.Chrome(options=chrome_opts)

    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)
    return driver


# ------------------------------------------------------------------ #
#  Xử lý 1 tài khoản (chạy trong 1 thread)
# ------------------------------------------------------------------ #
def run_account(account: dict, profile: dict, genlogin: GenLoginAPI):
    username = account["username"]
    profile_id = profile["id"]
    profile_name = profile.get("name", str(profile_id))

    for loop_idx in range(LOOP_COUNT):
        logger.info(f"[{username}] Bắt đầu – Profile: {profile_name} - Lần lặp {loop_idx + 1}/{LOOP_COUNT}")
        driver = None

        try:
            # 1. Start profile GenLogin
            start_data = genlogin.start_profile(profile_id)
            # GenLogin trả về: {"port": "58106", "wsEndpoint": "ws://127.0.0.1:58106/...", ...}
            debug_port = (
                start_data.get("remote_debugging_port")
                or start_data.get("port")
                or start_data.get("data", {}).get("remote_debugging_port")
                or start_data.get("data", {}).get("port")
            )
            # Fallback: trích port từ wsEndpoint "ws://127.0.0.1:PORT/..."
            if not debug_port and start_data.get("wsEndpoint"):
                try:
                    ws = start_data["wsEndpoint"]  # ws://127.0.0.1:58106/devtools/...
                    debug_port = ws.split("//")[1].split("/")[0].split(":")[1]
                except Exception:
                    pass
            if not debug_port:
                raise RuntimeError(f"Không lấy được debug port: {start_data}")

            logger.info(f"[{username}] Profile {profile_name} – port {debug_port}")
            time.sleep(5)  # Chờ Chrome khởi động hoàn toàn

            # 2. Kết nối Selenium
            driver = _connect_driver(int(debug_port))

            # 3. Login
            if not login(driver, account):
                raise RuntimeError("Login thất bại - dừng tài khoản")

            # 4. Navigate tới target
            if not navigate_to_target(driver):
                raise RuntimeError("Navigate thất bại")

            # 5. Tương tác
            result = interact_with_feed(driver)
            logger.info(f"[{username}] Kết quả: {result}")

        except Exception as e:
            err_msg = str(e)
            logger.error(f"[{username}] LỖI: {err_msg}")
            logger.debug(traceback.format_exc())
            mark_error(username, err_msg[:100])
            _log_error(username, err_msg)
            
            logger.warning(f"[{username}] Account báo lỗi, ngừng vòng lặp!")
            break

        finally:
            # 6. Luôn đóng profile dù thành công hay lỗi
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            try:
                genlogin.stop_profile(profile_id)
                logger.info(f"[{username}] Đã đóng profile {profile_name}")
            except Exception as e:
                logger.warning(f"[{username}] Stop profile lỗi: {e}")
        
        # Cho khoi dong lai giua cac vong lap
        if loop_idx < LOOP_COUNT - 1 and not is_skippable(username):
            wait_time = 10
            logger.info(f"[{username}] Đờỉ {wait_time}s trước khi mở lại profile...")
            time.sleep(wait_time)


# ------------------------------------------------------------------ #
#  Entry point
# ------------------------------------------------------------------ #
def main():
    logger.info("=" * 60)
    logger.info("  TWITTER 43MAX TOOL – KHỞI ĐỘNG")
    logger.info("=" * 60)

    # --- Kết nối GenLogin ---
    genlogin = GenLoginAPI()
    try:
        genlogin.login()
    except Exception as e:
        logger.error(f"Không thể kết nối GenLogin: {e}")
        return

    # --- Lấy danh sách profile ---
    profiles = genlogin.get_profiles_by_group_name()
    if not profiles:
        logger.error("Không có profile nào!")
        return
    logger.info(f"Tổng số profile: {len(profiles)}")

    # --- Đọc danh sách account ---
    accounts = load_accounts()
    if not accounts:
        logger.error("Không có account hợp lệ!")
        return
    logger.info(f"Tổng số account hợp lệ: {len(accounts)}")

    # --- Ghép account – profile (theo tên / username của account) ---
    pairs = []
    
    # Tạo list các profile đã được sử dụng để tránh 1 profile chạy cho 2 account
    used_profile_ids = set()

    for acc in accounts:
        uname = str(acc["username"]).lower()
        matched_profile = None

        # 1. Tìm chính xác 100% trước
        for p in profiles:
            p_name = str(p.get("name", "")).lower()
            if p_name == uname and p["id"] not in used_profile_ids:
                matched_profile = p
                break
        
        # 2. Nếu không có chính xác, tìm profile chứa username (hỗ trợ thêm _001, stt...)
        if not matched_profile:
            for p in profiles:
                p_name = str(p.get("name", "")).lower()
                if uname in p_name and p["id"] not in used_profile_ids:
                    matched_profile = p
                    break

        if matched_profile:
            pairs.append((acc, matched_profile))
            used_profile_ids.add(matched_profile["id"])
        else:
            logger.warning(f"[{acc['username']}] Không tìm thấy profile GenLogin nào khớp tên '{acc['username']}'")

    if not pairs and accounts and profiles:
        logger.warning("Không tìm thấy account nào match với profile!")

    if len(accounts) > len(pairs):
        logger.warning(
            f"Vài account ({len(accounts) - len(pairs)}) không có profile tương ứng!"
        )

    if not pairs:
        logger.error("Không có account nào ghép được với profile!")
        return

    logger.info(f"Chạy {len(pairs)} account với {MAX_THREADS} luồng đồng thời")

    # --- Chạy đa luồng ---
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {
            executor.submit(run_account, acc, prof, genlogin): acc["username"]
            for acc, prof in pairs
        }
        for future in as_completed(futures):
            username = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"[{username}] Unhandled exception: {e}")

    logger.info("=" * 60)
    logger.info("  HOÀN TẤT")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()