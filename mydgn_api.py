import hashlib
import time
import requests

BASE_URL = "https://api.mydgn.com"


class MyDGNError(Exception):
    pass


class MyDGNClient:
    def __init__(self, user: str, secret_key: str):
        self.user = user
        self.secret_key = secret_key

    def _auth(self, platform: str):
        timestamp = str(int(time.time()))
        raw = f"{platform}{self.user}{timestamp}{self.secret_key}"
        digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return {"user": self.user, "platform": platform, "timestamp": timestamp, "hash": digest}

    def get_transfer(self):
        params = {
            **self._auth("cons"),
            "maximumBuyOutPrice": 4000,
            "minimumBuyOutPrice": 0,
            "playerType": 1,
            "botapp": "Scar-Coin Telegram Bot",
        }
        try:
            response = requests.get(f"{BASE_URL}/transfers", params=params, timeout=20)
        except requests.RequestException as exc:
            raise MyDGNError("ارتباط با سرور myDGN برقرار نشد. کمی بعد دوباره تلاش کن.") from exc
        try:
            data = response.json()
        except ValueError:
            raise MyDGNError(f"پاسخ myDGN قابل خواندن نبود (HTTP {response.status_code}).")
        code = data.get("code", response.status_code)
        if response.status_code == 404 or code == 404:
            raise MyDGNError("در حال حاضر سفارش کنسول واجد شرایطی در myDGN موجود نیست.")
        if response.status_code == 429 or code == 429:
            raise MyDGNError("محدودیت درخواست myDGN فعال شده است. کمی صبر کن و دوباره امتحان کن.")
        if response.status_code == 403 or code == 403:
            raise MyDGNError("ربات API در myDGN غیرفعال است؛ برای فعال‌سازی با پشتیبانی myDGN تماس بگیر.")
        if response.status_code >= 400 or code not in (200, None):
            # Do not reveal credentials or request URL, which contains the signed hash.
            raise MyDGNError(f"myDGN درخواست را نپذیرفت (کد {code}). نام کاربری و فعال بودن API را بررسی کن.")
        if not isinstance(data, dict) or not data.get("transactionID"):
            raise MyDGNError("پاسخ myDGN سفارش معتبری نداشت.")
        return data
