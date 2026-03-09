"""
genlogin_api.py
Wrapper gọi GenLogin REST API.
Cấu trúc response thực tế: {"success":true, "data": {"items":[...], "pagination":{...}}}
"""

import requests
import logging
from settings import (
    GENLOGIN_API_URL,
    GENLOGIN_EMAIL,
    GENLOGIN_PASSWORD,
    GENLOGIN_GROUP,
)

logger = logging.getLogger(__name__)


class GenLoginAPI:
    def __init__(self):
        self.base_url = GENLOGIN_API_URL.rstrip("/")
        self.token = None
        self.session = requests.Session()

    # ------------------------------------------------------------------ #
    #  Auth
    # ------------------------------------------------------------------ #
    def login(self) -> str:
        """Đăng nhập GenLogin App, trả về access_token."""
        url = f"{self.base_url}/backend/auth/login"
        payload = {"username": GENLOGIN_EMAIL, "password": GENLOGIN_PASSWORD}
        resp = self.session.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        # Response: {"success": true, "data": {"access_token": "..."}}
        data = body.get("data") or body
        self.token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        logger.info("GenLogin login OK")
        return self.token

    def _ensure_token(self):
        if not self.token:
            self.login()

    # ------------------------------------------------------------------ #
    #  Profile groups
    # ------------------------------------------------------------------ #
    def get_groups(self) -> list:
        """Trả về list các group. Mỗi item có 'id' và 'name'."""
        self._ensure_token()
        url = f"{self.base_url}/backend/profile-groups"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        # Response: {"data": {"items": [...], "pagination": {...}}}
        data = body.get("data", {})
        return data.get("items") or data.get("list") or []

    def get_group_id(self, group_name: str) -> int | None:
        """Tìm ID của group theo tên (không phân biệt hoa thường)."""
        for g in self.get_groups():
            if isinstance(g, dict) and g.get("name", "").lower() == group_name.lower():
                return g["id"]
        return None

    # ------------------------------------------------------------------ #
    #  Profiles
    # ------------------------------------------------------------------ #
    def get_profiles(self, group_id: int = None, limit: int = 200) -> list:
        """Lấy danh sách tất cả profile có trong hệ thống bằng vòng lặp offset."""
        self._ensure_token()
        
        all_items = []
        current_offset = 0
        
        url = f"{self.base_url}/backend/profiles"
        
        while True:
            params = {
                "offset": current_offset,
                "limit": limit,
                "sort_by": "id",
                "order": "asc",
            }
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            data = body.get("data", {})
            items = data.get("items") or data.get("list") or []
            
            if not items:
                break
                
            all_items.extend(items)
            current_offset += limit
            
            # API có tổng số bản ghi không? Nếu không thì lặp đến khi items < limit hoặc rỗng.
            if len(items) < limit:
                break

        # Chuẩn hoá
        filtered_items = []
        for item in all_items:
            p_data = item.get("profile_data", {})
            if "name" not in item:
                item["name"] = p_data.get("name", str(item.get("id", "")))
            filtered_items.append(item)
            
        return filtered_items

    def get_profiles_by_group_name(self) -> list:
        """Lấy danh sách profile theo GENLOGIN_GROUP trong settings."""
        group_id = self.get_group_id(GENLOGIN_GROUP)
        if group_id is None:
            logger.warning(f"Không tìm thấy group '{GENLOGIN_GROUP}', dùng toàn bộ profile.")
            return self.get_profiles()
        logger.info(f"Group '{GENLOGIN_GROUP}' id={group_id}")
        return self.get_profiles(group_id=group_id)

    # ------------------------------------------------------------------ #
    #  Start / Stop
    # ------------------------------------------------------------------ #
    def start_profile(self, profile_id: int) -> dict:
        """
        Mở profile, trả về dict chứa remote_debugging_port.
        Response: {"data": {"remote_debugging_port": 12345, ...}}
        """
        self._ensure_token()
        url = f"{self.base_url}/backend/profiles/{profile_id}/start"
        resp = self.session.put(url, timeout=60)
        resp.raise_for_status()
        body = resp.json()
        return body.get("data") or body

    def stop_profile(self, profile_id: int):
        """Đóng profile."""
        self._ensure_token()
        url = f"{self.base_url}/backend/profiles/{profile_id}/stop"
        try:
            resp = self.session.put(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"Stop profile {profile_id} lỗi: {e}")
