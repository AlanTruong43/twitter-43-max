"""
account_status.py
Quản lý trạng thái từng tài khoản Twitter.
Ghi ra file account_status.txt, bỏ qua acc lỗi ở lần chạy sau.
"""

import os
import logging
from settings import ACCOUNT_STATUS_FILE

logger = logging.getLogger(__name__)

STATUS_ACTIVE  = "active"
STATUS_ERROR   = "error"
STATUS_BANNED  = "banned"


def load_status() -> dict:
    """Đọc file trạng thái, trả về dict {username: status}."""
    status = {}
    if not os.path.exists(ACCOUNT_STATUS_FILE):
        return status
    with open(ACCOUNT_STATUS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "|" in line:
                username, _, st = line.partition("|")
                status[username.strip()] = st.strip()
    return status


def _save_status(status: dict):
    with open(ACCOUNT_STATUS_FILE, "w", encoding="utf-8") as f:
        for username, st in status.items():
            f.write(f"{username}|{st}\n")


def mark_error(username: str, reason: str = ""):
    status = load_status()
    status[username] = STATUS_ERROR + (f":{reason}" if reason else "")
    _save_status(status)
    logger.warning(f"[{username}] → Đánh dấu ERROR: {reason}")


def mark_active(username: str):
    status = load_status()
    status[username] = STATUS_ACTIVE
    _save_status(status)
    logger.info(f"[{username}] → Đánh dấu ACTIVE")


def is_skippable(username: str) -> bool:
    """True nếu account đang ở trạng thái error/banned → bỏ qua."""
    status = load_status()
    st = status.get(username, "")
    return st.startswith(STATUS_ERROR) or st.startswith(STATUS_BANNED)
