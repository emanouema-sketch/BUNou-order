"""
تمام مقادیر حساس و قابل‌تنظیم از Environment Variables خوانده می‌شوند —
هیچ‌کدام داخل کد هاردکد نشده‌اند.
"""
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
ADMIN_COMMAND = os.environ.get("ADMIN_COMMAND", "nouh95")
CARD_NUMBER = os.environ.get("CARD_NUMBER", "0000-0000-0000-0000")
CARD_HOLDER_NAME = os.environ.get("CARD_HOLDER_NAME", "نام صاحب حساب")

# دیتابیس: روی Railway حتما یک Volume به همین مسیر وصل کنید تا اطلاعات
# با هر Deploy/Restart پاک نشود (در راهنمای پایانی توضیح داده شده).
DB_PATH = os.environ.get("DB_PATH", "/data/nounilla.db")

# بعد از این مدت (ثانیه) بدون تکمیل خرید، سفارش «رهاشده» در نظر گرفته می‌شود.
ABANDON_SECONDS = int(os.environ.get("ABANDON_SECONDS", "1800"))  # 30 دقیقه

STORE_NAME = "NouNilla"
