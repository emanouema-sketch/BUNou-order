"""
ماژول محاسبه هزینه ارسال — به‌صورت جدا از بقیه کد نگه داشته شده تا بعدا
بتوانید هزینه‌ها را بر اساس شهر/وزن/مبلغ سفارش تغییر دهید، بدون لمس بقیه پروژه.

هر گزینه یک دیکشنری با کلیدهای زیر است:
  method : شناسه داخلی ("post" یا "courier")
  label  : متنی که به مشتری نمایش داده می‌شود
  cost   : مبلغی که به‌صورت آنلاین از مشتری گرفته می‌شود (تومان)
  cod    : True یعنی هزینه واقعی جدا و نقدی (پس‌کرایه) است و در جمع آنلاین حساب نمی‌شود
"""

TEHRAN_POST_COST = 130000
SHAHRESTAN_POST_COST = 140000


def get_shipping_options(province: str, city: str = None, order_subtotal: int = None, weight: float = None):
    """
    امضای تابع عمداً چند پارامتر اضافه (city/order_subtotal/weight) دارد که
    فعلاً استفاده نمی‌شوند، تا بعداً بدون تغییر امضای تابع در بقیه فایل‌ها،
    بتوانید منطق قیمت‌گذاری پیچیده‌تری (بر اساس شهر/وزن/مبلغ) اضافه کنید.
    """
    if province == "تهران":
        return [
            {"method": "post", "label": "پست پیشتاز", "cost": TEHRAN_POST_COST, "cod": False},
            {"method": "courier", "label": "پیک موتوری (پس‌کرایه)", "cost": 0, "cod": True},
        ]
    return [
        {"method": "post", "label": "پست پیشتاز", "cost": SHAHRESTAN_POST_COST, "cod": False},
    ]


def get_option(province: str, method: str):
    for opt in get_shipping_options(province):
        if opt["method"] == method:
            return opt
    return None
