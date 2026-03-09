"""
navigate.py
Điều hướng tới trang target Twitter:
  - Theo username: vào thẳng https://x.com/<username>
  - Theo hashtag: tìm hashtag → lướt → phát hiện tweet của TARGET_USERNAME → vào trang đó
"""

import time
import random
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from settings import TARGET_MODE, TARGET_USERNAME, TARGET_HASHTAG, DELAY_MIN, DELAY_MAX

logger = logging.getLogger(__name__)


def _sleep():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


# ------------------------------------------------------------------ #
#  Điều hướng theo username
# ------------------------------------------------------------------ #
def go_to_username(driver: WebDriver, username: str = None) -> bool:
    target = username or TARGET_USERNAME
    url = f"https://x.com/{target}"
    logger.info(f"Điều hướng tới {url}")
    driver.get(url)
    try:
        # Chờ timeline profile load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@data-testid="primaryColumn"]')
            )
        )
        _sleep()
        return True
    except TimeoutException:
        logger.error(f"Không thể load trang {url}")
        return False


# ------------------------------------------------------------------ #
#  Điều hướng theo hashtag
# ------------------------------------------------------------------ #
def _search_hashtag(driver: WebDriver, hashtag: str):
    """Tìm hashtag qua thanh search của Twitter."""
    hashtag = hashtag.lstrip("#")
    search_url = f"https://x.com/search?q=%23{hashtag}&src=typed_query&f=live"
    logger.info(f"Tìm kiếm #{hashtag}")
    driver.get(search_url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@data-testid="primaryColumn"]')
            )
        )
        time.sleep(2)
    except TimeoutException:
        logger.error(f"Không load được trang tìm #{hashtag}")


def _scroll_and_find_user(driver: WebDriver, target_username: str, n_scroll: int) -> bool:
    """
    Lướt n_scroll lần, kiểm tra xem có tweet nào của target_username không.
    Nếu tìm thấy → click vào username đó → True.
    """
    for i in range(n_scroll):
        # Tìm tất cả link user display trên màn hình hiện tại
        try:
            user_links = driver.find_elements(
                By.XPATH,
                f'//a[@href="/{target_username}" or @href="/{target_username.lower()}"]'
            )
            if user_links:
                logger.info(f"Tìm thấy tweet của @{target_username} lần scroll {i+1}")
                user_links[0].click()
                time.sleep(3)
                return True
        except Exception as e:
            logger.debug(f"Scroll {i+1} – lỗi tìm user: {e}")

        # Scroll xuống
        driver.execute_script("window.scrollBy(0, window.innerHeight * 1.5);")
        _sleep()

    return False


def go_to_via_hashtag(driver: WebDriver) -> bool:
    """
    Tìm TARGET_HASHTAG, lướt 5–10 tweet.
    Nếu thấy tweet của TARGET_USERNAME → vào trang đó.
    Nếu không thấy → vào thẳng bằng username.
    """
    from settings import SCROLL_MIN, SCROLL_MAX
    n_scroll = random.randint(SCROLL_MIN, SCROLL_MAX)

    _search_hashtag(driver, TARGET_HASHTAG)
    found = _scroll_and_find_user(driver, TARGET_USERNAME, n_scroll)

    if found:
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@data-testid="primaryColumn"]')
                )
            )
            _sleep()
            return True
        except TimeoutException:
            pass

    # Fallback: vào thẳng
    logger.info(f"Không thấy tweet của @{TARGET_USERNAME} qua hashtag, vào thẳng profile.")
    return go_to_username(driver)


# ------------------------------------------------------------------ #
#  Hàm main điều phối
# ------------------------------------------------------------------ #
def navigate_to_target(driver: WebDriver) -> bool:
    """Điều hướng tới trang target theo TARGET_MODE trong settings."""
    if TARGET_MODE == "username":
        return go_to_username(driver)
    elif TARGET_MODE == "hashtag":
        return go_to_via_hashtag(driver)
    else:
        logger.error(f"TARGET_MODE không hợp lệ: {TARGET_MODE!r}")
        return False
