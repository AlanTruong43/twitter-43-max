"""
interact.py
Tương tác với các tweet trên trang target: like + retweet.
Tỉ lệ % lấy từ settings.py, có delay ngẫu nhiên giữa các hành động.
"""

import time
import random
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)

from settings import (
    LIKE_RATE,
    RETWEET_RATE,
    SCROLL_MIN,
    SCROLL_MAX,
    DELAY_MIN,
    DELAY_MAX,
)

logger = logging.getLogger(__name__)


def _sleep(extra=0):
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX) + extra)


def _roll(rate: int) -> bool:
    """True nếu ngẫu nhiên <= rate%."""
    return random.randint(1, 100) <= rate


# ------------------------------------------------------------------ #
#  Like tweet
# ------------------------------------------------------------------ #
def like_tweet(driver: WebDriver, tweet_el) -> bool:
    """Click like nếu chưa like. Trả về True nếu thành công."""
    try:
        like_btn = tweet_el.find_element(
            By.XPATH, './/button[@data-testid="like"]'
        )
        aria = like_btn.get_attribute("aria-label") or ""
        if "Liked" in aria or "liked" in aria.lower():
            logger.debug("Bài đã được like, bỏ qua.")
            return False
        like_btn.click()
        logger.info("✅ Like OK")
        return True
    except (NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException) as e:
        logger.debug(f"Like thất bại: {e}")
        return False


# ------------------------------------------------------------------ #
#  Retweet tweet
# ------------------------------------------------------------------ #
def retweet_tweet(driver: WebDriver, tweet_el) -> bool:
    """Click retweet → xác nhận. Trả về True nếu thành công."""
    try:
        rt_btn = tweet_el.find_element(
            By.XPATH, './/button[@data-testid="retweet"]'
        )
        aria = rt_btn.get_attribute("aria-label") or ""
        if "Retweeted" in aria or "Undo" in aria:
            logger.debug("Bài đã retweet, bỏ qua.")
            return False
        rt_btn.click()
        time.sleep(1)

        # Popup xác nhận "Retweet"
        confirm = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//div[@data-testid="retweetConfirm"]')
            )
        )
        confirm.click()
        logger.info("🔁 Retweet OK")
        return True
    except (TimeoutException, NoSuchElementException,
            ElementNotInteractableException, StaleElementReferenceException) as e:
        logger.debug(f"Retweet thất bại: {e}")
        return False


# ------------------------------------------------------------------ #
#  Thu thập tweet elements có thể tương tác
# ------------------------------------------------------------------ #
def _get_visible_tweets(driver: WebDriver) -> list:
    """Trả về list các tweet article element hiện có trên viewport."""
    try:
        return driver.find_elements(
            By.XPATH, '//article[@data-testid="tweet"]'
        )
    except Exception:
        return []


# ------------------------------------------------------------------ #
#  Hàm chính: lướt + tương tác
# ------------------------------------------------------------------ #
def interact_with_feed(driver: WebDriver):
    """
    Lướt ngẫu nhiên SCROLL_MIN–SCROLL_MAX lần trên trang profile target.
    Với mỗi tweet nhìn thấy: like và/hoặc retweet theo tỉ lệ % cài đặt.
    Có delay ngẫu nhiên giữa từng hành động.
    """
    n_scroll = random.randint(SCROLL_MIN, SCROLL_MAX)
    logger.info(f"Bắt đầu tương tác, dự kiến lướt {n_scroll} lần")

    total_likes = 0
    total_rts = 0
    seen_tweets = set()   # tránh tương tác lặp

    for scroll_i in range(n_scroll):
        tweets = _get_visible_tweets(driver)
        logger.info(f"Scroll {scroll_i+1}/{n_scroll} – thấy {len(tweets)} tweet")

        for tweet in tweets:
            try:
                # Dùng id nội bộ element để dedup
                tweet_id = tweet.id
                if tweet_id in seen_tweets:
                    continue
                seen_tweets.add(tweet_id)

                # Cuộn tweet vào giữa màn hình
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", tweet
                )
                time.sleep(0.5)

                # --- Like ---
                if _roll(LIKE_RATE):
                    liked = like_tweet(driver, tweet)
                    if liked:
                        total_likes += 1
                    _sleep()

                # --- Retweet ---
                if _roll(RETWEET_RATE):
                    rted = retweet_tweet(driver, tweet)
                    if rted:
                        total_rts += 1
                    _sleep()

            except StaleElementReferenceException:
                logger.debug("Tweet element stale, bỏ qua.")
            except Exception as e:
                logger.debug(f"Lỗi khi xử lý tweet: {e}")

        # Scroll xuống để load thêm tweet
        driver.execute_script("window.scrollBy(0, window.innerHeight * 1.2);")
        _sleep(extra=1)

    logger.info(f"Hoàn tất: {total_likes} likes, {total_rts} retweets")
    return {"likes": total_likes, "retweets": total_rts}
