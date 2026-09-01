def toman(n: int) -> str:
    """عدد را با جداکننده هزارگان و واحد تومان نمایش می‌دهد."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 0
    return f"{n:,}".replace(",", "٬") + " تومان"


def clean_digits(text: str) -> str:
    """اعداد فارسی/عربی را به انگلیسی تبدیل و فاصله/خط‌تیره را حذف می‌کند."""
    fa = "۰۱۲۳۴۵۶۷۸۹"
    ar = "٠١٢٣٤٥٦٧٨٩"
    out = []
    for ch in text.strip():
        if ch in fa:
            out.append(str(fa.index(ch)))
        elif ch in ar:
            out.append(str(ar.index(ch)))
        elif ch.isdigit():
            out.append(ch)
    return "".join(out)


def is_valid_phone(text: str) -> bool:
    digits = clean_digits(text)
    return digits.isdigit() and len(digits) >= 10
