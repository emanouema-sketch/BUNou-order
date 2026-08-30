import os
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

import db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
CARD_NUMBER = os.environ.get("CARD_NUMBER", "6037-XXXX-XXXX-XXXX")
CARD_HOLDER = os.environ.get("CARD_HOLDER_NAME", "نام صاحب حساب")

OTHER_CITY = "🏙 شهر دیگر (تایپ می‌کنم)"

# Major cities per province. Not a literally exhaustive list of every town —
# customers can always pick "شهر دیگر" and type their city by hand.
CITIES = {
    "تهران": ["تهران", "شهریار", "اسلام‌شهر", "ری", "پاکدشت", "ورامین", "دماوند", "رباط‌کریم", "پردیس", "قدس"],
    "البرز": ["کرج", "فردیس", "نظرآباد", "اشتهارد", "طالقان", "هشتگرد"],
    "اصفهان": ["اصفهان", "کاشان", "نجف‌آباد", "خمینی‌شهر", "شاهین‌شهر", "نطنز", "اردستان", "فولادشهر", "مبارکه", "گلپایگان"],
    "فارس": ["شیراز", "مرودشت", "جهرم", "کازرون", "فسا", "لار", "داراب", "آباده", "فیروزآباد", "اقلید"],
    "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت‌حیدریه", "کاشمر", "قوچان", "تربت‌جام", "چناران", "سرخس", "گناباد"],
    "آذربایجان شرقی": ["تبریز", "مراغه", "میانه", "مرند", "اهر", "سراب", "بناب", "شبستر", "آذرشهر", "جلفا"],
    "آذربایجان غربی": ["ارومیه", "خوی", "میاندوآب", "بوکان", "مهاباد", "سلماس", "پیرانشهر", "نقده", "ماکو", "سردشت"],
    "خوزستان": ["اهواز", "آبادان", "خرمشهر", "دزفول", "بندر ماهشهر", "شوشتر", "اندیمشک", "بهبهان", "شوش", "ایذه"],
    "مازندران": ["ساری", "بابل", "آمل", "قائم‌شهر", "بهشهر", "تنکابن", "رامسر", "نوشهر", "چالوس", "بابلسر"],
    "گیلان": ["رشت", "بندر انزلی", "لاهیجان", "لنگرود", "آستارا", "تالش", "رودسر", "صومعه‌سرا", "فومن", "ماسال"],
    "کرمان": ["کرمان", "رفسنجان", "سیرجان", "بم", "جیرفت", "زرند", "شهربابک", "کهنوج", "بردسیر", "راور"],
    "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب", "سنقر", "پاوه", "صحنه", "جوانرود", "سرپل‌ذهاب", "هرسین", "کنگاور", "قصرشیرین"],
    "یزد": ["یزد", "میبد", "اردکان", "بافق", "تفت", "ابرکوه", "مهریز", "بهاباد"],
    "هرمزگان": ["بندرعباس", "میناب", "بندرلنگه", "قشم", "رودان", "جاسک", "حاجی‌آباد", "کیش"],
    "سیستان و بلوچستان": ["زاهدان", "زابل", "چابهار", "ایرانشهر", "سراوان", "خاش", "کنارک", "نیک‌شهر"],
    "گلستان": ["گرگان", "گنبد کاووس", "علی‌آباد کتول", "آق‌قلا", "کردکوی", "بندر ترکمن", "مینودشت", "آزادشهر"],
    "اردبیل": ["اردبیل", "مشکین‌شهر", "پارس‌آباد", "خلخال", "گرمی", "بیله‌سوار", "نمین", "نیر"],
    "قزوین": ["قزوین", "تاکستان", "البرز", "آبیک", "بویین‌زهرا", "محمدیه"],
    "قم": ["قم", "سلفچگان", "جعفریه", "کهک"],
    "زنجان": ["زنجان", "ابهر", "قیدار", "ماهنشان", "طارم", "خرمدره"],
    "همدان": ["همدان", "ملایر", "نهاوند", "تویسرکان", "اسدآباد", "کبودراهنگ", "رزن", "بهار"],
    "لرستان": ["خرم‌آباد", "بروجرد", "دورود", "الیگودرز", "کوهدشت", "ازنا", "الشتر", "پلدختر"],
    "مرکزی": ["اراک", "ساوه", "خمین", "محلات", "دلیجان", "شازند", "تفرش", "آشتیان"],
    "بوشهر": ["بوشهر", "برازجان", "گناوه", "کنگان", "دیر", "دیلم", "جم", "عسلویه"],
    "چهارمحال و بختیاری": ["شهرکرد", "بروجن", "فارسان", "لردگان", "کیار", "اردل"],
    "کهگیلویه و بویراحمد": ["یاسوج", "گچساران", "دهدشت", "سی‌سخت", "لیکک"],
    "ایلام": ["ایلام", "دهلران", "آبدانان", "دره‌شهر", "ایوان", "مهران", "چرداول"],
    "کردستان": ["سنندج", "سقز", "مریوان", "بانه", "قروه", "بیجار", "کامیاران", "دیواندره"],
    "سمنان": ["سمنان", "شاهرود", "دامغان", "گرمسار", "مهدی‌شهر", "ایوانکی"],
    "خراسان شمالی": ["بجنورد", "شیروان", "اسفراین", "آشخانه", "فاروج", "جاجرم"],
    "خراسان جنوبی": ["بیرجند", "قاین", "فردوس", "طبس", "نهبندان", "سربیشه"],
}
PROVINCES = list(CITIES.keys())

(
    SELECT_PRODUCTS, ASK_VENDOR_CHOICE, ASK_VENDOR_CODE, ASK_DISCOUNT_CHOICE, ASK_DISCOUNT_CODE,
    ASK_PROVINCE, ASK_CITY, ASK_ADDRESS, ASK_PHONE, ASK_SHIPPING, CONFIRM, WAIT_RECEIPT,
) = range(12)


def toman(n):
    return f"{n:,} تومان".replace(",", "٬")


def cart_summary_text(cart):
    if not cart:
        return "سبد خرید شما خالی است."
    lines = []
    total = 0
    for pid, qty in cart.items():
        p = db.get_product(pid)
        if not p:
            continue
        line_total = p["price"] * qty
        total += line_total
        lines.append(f"• {p['name']} × {qty} = {toman(line_total)}")
    lines.append(f"\nجمع کالاها: {toman(total)}")
    return "\n".join(lines)


def cart_subtotal(cart):
    total = 0
    for pid, qty in cart.items():
        p = db.get_product(pid)
        if p:
            total += p["price"] * qty
    return total


def products_keyboard(cart):
    rows = []
    for p in db.list_products():
        qty = cart.get(p["id"], 0)
        label = f"{p['name']} — {toman(p['price'])}" + (f"  (در سبد: {qty})" if qty else "")
        rows.append([InlineKeyboardButton(label, callback_data=f"add:{p['id']}")])
    rows.append([InlineKeyboardButton("✅ پایان انتخاب / ادامه", callback_data="done")])
    return InlineKeyboardMarkup(rows)


def shipping_cost_for(province, method):
    """Returns (cost, is_cash_on_delivery)."""
    if method == "courier":
        return 0, True  # پس‌کرایه: پرداخت نقدی به پیک هنگام تحویل
    return (45000 if province == "تهران" else 120000), False


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["cart"] = {}
    await update.message.reply_text(
        "سلام! به فروشگاه B.U.Nou خوش آمدید. 🛍\n"
        "برای هر محصولی که می‌خواهید روی آن بزنید (چند بار بزنید برای تعداد بیشتر)."
        "\nوقتی انتخابتان تمام شد، «پایان انتخاب / ادامه» را بزنید.",
    )
    await update.message.reply_text(
        cart_summary_text(context.user_data["cart"]),
        reply_markup=products_keyboard(context.user_data["cart"]),
    )
    return SELECT_PRODUCTS


async def select_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart = context.user_data.setdefault("cart", {})

    if query.data == "done":
        if not cart:
            await query.answer("سبد خرید خالی است.", show_alert=True)
            return SELECT_PRODUCTS
        await query.edit_message_text(cart_summary_text(cart))
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("بله، کد فروش دارم", callback_data="vendor_yes"),
              InlineKeyboardButton("خیر", callback_data="vendor_no")]]
        )
        await query.message.reply_text("آیا کد فروش (کد فروشنده) دارید؟", reply_markup=keyboard)
        return ASK_VENDOR_CHOICE

    pid = int(query.data.split(":")[1])
    cart[pid] = cart.get(pid, 0) + 1
    await query.edit_message_text(cart_summary_text(cart), reply_markup=products_keyboard(cart))
    return SELECT_PRODUCTS


# ---------------- VENDOR (فروشنده) CODE ----------------
async def ask_vendor_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "vendor_no":
        context.user_data["vendor_code"] = None
        return await ask_discount_choice_entry(query.message, context)
    await query.edit_message_text("کد فروش را وارد کنید (مثلا NEGAR):")
    return ASK_VENDOR_CODE


async def ask_vendor_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    vendor = db.get_vendor_by_code(code)
    if not vendor:
        await update.message.reply_text("این کد فروش معتبر نیست. دوباره وارد کنید یا /skip را بزنید.")
        return ASK_VENDOR_CODE
    context.user_data["vendor_code"] = code
    await update.message.reply_text(f"کد فروش «{code}» ثبت شد. ✅")
    return await ask_discount_choice_entry(update.message, context)


async def skip_vendor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["vendor_code"] = None
    return await ask_discount_choice_entry(update.message, context)


# ---------------- DISCOUNT CODE ----------------
async def ask_discount_choice_entry(message, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("بله، کد تخفیف دارم", callback_data="disc_yes"),
          InlineKeyboardButton("خیر", callback_data="disc_no")]]
    )
    await message.reply_text("آیا کد تخفیف دارید؟", reply_markup=keyboard)
    return ASK_DISCOUNT_CHOICE


async def ask_discount_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "disc_no":
        context.user_data["discount_code"] = None
        context.user_data["discount_amount"] = 0
        return await ask_province_entry(query.message, context)
    await query.edit_message_text("کد تخفیف را وارد کنید:")
    return ASK_DISCOUNT_CODE


async def ask_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    disc = db.get_discount(code)
    if not disc:
        await update.message.reply_text("این کد تخفیف معتبر نیست. دوباره وارد کنید یا /skip را بزنید.")
        return ASK_DISCOUNT_CODE
    subtotal = cart_subtotal(context.user_data["cart"])
    amount = round(subtotal * disc["percent"] / 100)
    context.user_data["discount_code"] = code
    context.user_data["discount_amount"] = amount
    await update.message.reply_text(f"کد تخفیف «{code}» ({disc['percent']}٪) اعمال شد. ✅ تخفیف: {toman(amount)}")
    return await ask_province_entry(update.message, context)


async def skip_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["discount_code"] = None
    context.user_data["discount_amount"] = 0
    return await ask_province_entry(update.message, context)


# ---------------- ADDRESS: PROVINCE -> CITY -> FULL ADDRESS -> PHONE ----------------
async def ask_province_entry(message, context: ContextTypes.DEFAULT_TYPE):
    rows = [PROVINCES[i:i + 2] for i in range(0, len(PROVINCES), 2)]
    keyboard = ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)
    await message.reply_text("استان محل تحویل را انتخاب کنید:", reply_markup=keyboard)
    return ASK_PROVINCE


async def ask_province(update: Update, context: ContextTypes.DEFAULT_TYPE):
    province = update.message.text.strip()
    if province not in PROVINCES:
        await update.message.reply_text("لطفا یکی از استان‌های نمایش داده‌شده را انتخاب کنید.")
        return ASK_PROVINCE
    context.user_data["province"] = province
    context.user_data["manual_city_mode"] = False

    cities = CITIES[province] + [OTHER_CITY]
    rows = [cities[i:i + 2] for i in range(0, len(cities), 2)]
    keyboard = ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"شهر خود را در استان {province} انتخاب کنید:", reply_markup=keyboard)
    return ASK_CITY


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if context.user_data.get("manual_city_mode"):
        context.user_data["city"] = text
        context.user_data["manual_city_mode"] = False
        await update.message.reply_text("آدرس دقیق (خیابان، پلاک، واحد) را بنویسید:", reply_markup=ReplyKeyboardRemove())
        return ASK_ADDRESS

    if text == OTHER_CITY:
        context.user_data["manual_city_mode"] = True
        await update.message.reply_text("نام شهر خود را تایپ کنید:", reply_markup=ReplyKeyboardRemove())
        return ASK_CITY

    province = context.user_data.get("province")
    if province and text not in CITIES.get(province, []):
        await update.message.reply_text("لطفا یکی از شهرهای نمایش داده‌شده را انتخاب کنید، یا «شهر دیگر» را بزنید.")
        return ASK_CITY

    context.user_data["city"] = text
    await update.message.reply_text("آدرس دقیق (خیابان، پلاک، واحد) را بنویسید:", reply_markup=ReplyKeyboardRemove())
    return ASK_ADDRESS


async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text.strip()
    await update.message.reply_text("شماره تلفن همراه خود را وارد کنید (مثلا 09123456789):")
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    digits = phone.replace(" ", "").replace("-", "")
    if not digits.isdigit() or len(digits) < 10:
        await update.message.reply_text("شماره تلفن معتبر به نظر نمی‌رسد. دوباره وارد کنید (مثلا 09123456789):")
        return ASK_PHONE
    context.user_data["phone"] = digits

    province = context.user_data["province"]
    post_cost, _ = shipping_cost_for(province, "post")
    buttons = [[InlineKeyboardButton(f"پست پیشتاز — {toman(post_cost)}", callback_data="ship:post")]]
    if province == "تهران":
        buttons.append([InlineKeyboardButton("پیک موتوری (پس‌کرایه، در محل پرداخت می‌شود)", callback_data="ship:courier")])
    await update.message.reply_text("روش ارسال را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_SHIPPING


# ---------------- SHIPPING + CONFIRM ----------------
async def ask_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split(":")[1]
    province = context.user_data["province"]
    shipping_cost, is_cod = shipping_cost_for(province, method)

    context.user_data["shipping_method"] = method
    context.user_data["shipping_cost"] = shipping_cost
    context.user_data["shipping_cod"] = is_cod

    cart = context.user_data["cart"]
    subtotal = cart_subtotal(cart)
    discount_amount = context.user_data.get("discount_amount", 0)
    total = subtotal - discount_amount + shipping_cost
    context.user_data["subtotal"] = subtotal
    context.user_data["total"] = total

    shipping_label = "پست پیشتاز" if method == "post" else "پیک موتوری (پس‌کرایه)"
    shipping_line = f"روش ارسال: {shipping_label}"
    shipping_line += " — هزینه پیک در محل تحویل از شما دریافت می‌شود." if is_cod else f" ({toman(shipping_cost)})"

    summary = (
        cart_summary_text(cart) + "\n\n"
        f"کد فروش: {context.user_data.get('vendor_code') or 'ندارد'}\n"
        f"کد تخفیف: {context.user_data.get('discount_code') or 'ندارد'}"
        + (f" (- {toman(discount_amount)})" if discount_amount else "") + "\n"
        f"{shipping_line}\n"
        f"استان/شهر: {province} / {context.user_data['city']}\n"
        f"آدرس: {context.user_data['address']}\n"
        f"تلفن: {context.user_data['phone']}\n\n"
        f"💰 مبلغ قابل پرداخت آنلاین: {toman(total)}"
        + ("\n(هزینه پیک جدا و نقدی است)" if is_cod else "")
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ تایید و ادامه به پرداخت", callback_data="confirm"),
          InlineKeyboardButton("❌ انصراف", callback_data="cancel")]]
    )
    await query.edit_message_text(summary, reply_markup=keyboard)
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("سفارش لغو شد. برای شروع دوباره /start را بزنید.")
        return ConversationHandler.END

    d = context.user_data
    cart = d["cart"]
    items = [{"name": db.get_product(pid)["name"], "qty": qty, "price": db.get_product(pid)["price"]} for pid, qty in cart.items()]
    items_text = "؛ ".join(f"{it['name']} × {it['qty']}" for it in items)

    order_id = db.create_order({
        "user_id": update.effective_user.id,
        "username": update.effective_user.username or update.effective_user.first_name,
        "phone": d.get("phone", ""),
        "items_text": items_text,
        "items": items,
        "subtotal": d["subtotal"],
        "vendor_code": d.get("vendor_code"),
        "discount_code": d.get("discount_code"),
        "discount_amount": d.get("discount_amount", 0),
        "shipping_method": d["shipping_method"],
        "shipping_cost": d["shipping_cost"],
        "shipping_cod": d.get("shipping_cod", False),
        "total": d["total"],
        "province": d["province"],
        "city": d["city"],
        "address": d["address"],
    })
    context.user_data["order_id"] = order_id

    await query.edit_message_text(
        f"سفارش شما با شماره #{order_id} ثبت شد.\n\n"
        f"لطفا مبلغ {toman(d['total'])} را به شماره کارت زیر واریز کنید:\n\n"
        f"💳 {CARD_NUMBER}\n👤 به نام: {CARD_HOLDER}\n\n"
        "سپس عکس رسید یا فیش واریزی را همین‌جا برای ما ارسال کنید."
    )

    # let the admin know a cart/order started even before payment proof arrives
    if ADMIN_CHAT_ID:
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            f"🕐 سفارش #{order_id} ثبت شد و در انتظار پرداخت است (هنوز فیش ارسال نشده).\n"
            f"مشتری: @{context.user_data.get('username') or update.effective_user.username or update.effective_user.first_name}\n"
            f"مبلغ: {toman(d['total'])}\n"
            f"برای دیدن همه سفارش‌های ناقص: /pending_orders"
        )
    return WAIT_RECEIPT


# ---------------- RECEIPT + ADMIN APPROVAL ----------------
async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("لطفا تصویر فیش واریزی را ارسال کنید.")
        return WAIT_RECEIPT

    order_id = context.user_data["order_id"]
    file_id = update.message.photo[-1].file_id
    db.attach_receipt(order_id, file_id)
    order = db.get_order(order_id)

    await update.message.reply_text(
        "فیش شما دریافت شد. ✅ سفارش شما پس از تایید مدیر نهایی می‌شود؛ نتیجه را همین‌جا اطلاع می‌دهیم."
    )

    if ADMIN_CHAT_ID:
        shipping_label = "پست پیشتاز" if order["shipping_method"] == "post" else "پیک موتوری (پس‌کرایه)"
        caption = (
            f"🧾 رسید پرداخت سفارش #{order_id}\n\n"
            f"مشتری: @{order['username']}\n"
            f"تلفن: {order['phone']}\n"
            f"اقلام: {order['items_text']}\n"
            f"کد فروش: {order['vendor_code'] or 'ندارد'}\n"
            f"کد تخفیف: {order['discount_code'] or 'ندارد'}\n"
            f"ارسال: {shipping_label}\n"
            f"مقصد: {order['province']}، {order['city']}، {order['address']}\n"
            f"💰 مبلغ: {toman(order['total'])}"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ تایید سفارش", callback_data=f"approve:{order_id}"),
              InlineKeyboardButton("❌ رد سفارش", callback_data=f"reject:{order_id}")]]
        )
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=file_id, caption=caption, reply_markup=keyboard)

    return ConversationHandler.END


async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, order_id = query.data.split(":")
    order_id = int(order_id)
    order = db.get_order(order_id)
    if not order:
        await query.edit_message_caption("این سفارش پیدا نشد.")
        return

    if action == "approve":
        db.set_order_status(order_id, "confirmed")
        await query.edit_message_caption(query.message.caption + "\n\n✅ تایید شد.")
        await context.bot.send_message(order["user_id"], f"سفارش #{order_id} شما تایید و ثبت نهایی شد. ممنون از خرید شما از B.U.Nou 🌸")
    else:
        db.set_order_status(order_id, "rejected")
        await query.edit_message_caption(query.message.caption + "\n\n❌ رد شد.")
        await context.bot.send_message(order["user_id"], f"متاسفانه فیش پرداخت سفارش #{order_id} تایید نشد. لطفا با پشتیبانی تماس بگیرید یا فیش صحیح را دوباره ارسال کنید.")


# ---------------- CANCEL ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد. برای شروع دوباره /start را بزنید.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ---------------- ADMIN MANAGEMENT COMMANDS ----------------
def is_admin(update: Update):
    return ADMIN_CHAT_ID and str(update.effective_chat.id) == str(ADMIN_CHAT_ID)


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text(
        "دستورهای مدیریت:\n"
        "/add_product نام|قیمت|توضیح\n"
        "/list_products\n"
        "/remove_product شناسه\n"
        "/set_price شناسه|قیمت_جدید\n"
        "/add_vendor نام|کد|درصد_کمیسیون\n"
        "/list_vendors\n"
        "/add_discount کد|درصد|کد_فروشنده(اختیاری)\n"
        "/pending_orders — سفارش‌های ناقص (پرداخت‌نشده)\n"
        "/stats — آمار فروش"
    )


async def add_product_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        name, price, desc = update.message.text.split(" ", 1)[1].split("|")
        db.add_product(name.strip(), int(price.strip()), desc.strip())
        await update.message.reply_text(f"محصول «{name.strip()}» اضافه شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /add_product نام|قیمت|توضیح")


async def list_products_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    lines = [f"#{p['id']} — {p['name']} — {toman(p['price'])}" for p in db.list_products()]
    await update.message.reply_text("\n".join(lines) or "محصولی ثبت نشده.")


async def remove_product_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        pid = int(update.message.text.split(" ", 1)[1].strip())
        db.remove_product(pid)
        await update.message.reply_text(f"محصول #{pid} حذف شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /remove_product شناسه")


async def set_price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        pid, price = update.message.text.split(" ", 1)[1].split("|")
        db.update_price(int(pid.strip()), int(price.strip()))
        await update.message.reply_text("قیمت به‌روزرسانی شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /set_price شناسه|قیمت_جدید")


async def add_vendor_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        name, code, rate = update.message.text.split(" ", 1)[1].split("|")
        db.add_vendor(name.strip(), code.strip(), float(rate.strip()))
        await update.message.reply_text(f"فروشنده «{name.strip()}» با کد {code.strip().upper()} اضافه شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /add_vendor نام|کد|درصد_کمیسیون")


async def list_vendors_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    lines = [f"{v['name']} — {v['code']} — {v['commission_rate']}٪" for v in db.list_vendors()]
    await update.message.reply_text("\n".join(lines) or "فروشنده‌ای ثبت نشده.")


async def add_discount_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        parts = update.message.text.split(" ", 1)[1].split("|")
        code, percent = parts[0].strip(), int(parts[1].strip())
        vendor_code = parts[2].strip() if len(parts) > 2 else None
        db.add_discount(code, percent, vendor_code)
        await update.message.reply_text(f"کد تخفیف «{code.upper()}» ({percent}٪) فعال شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /add_discount کد|درصد|کد_فروشنده(اختیاری)")


async def pending_orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    rows = db.pending_orders()
    if not rows:
        await update.message.reply_text("هیچ سفارش ناقص/پرداخت‌نشده‌ای وجود ندارد. ✅")
        return
    lines = ["🕐 سفارش‌های ناقص (پرداخت یا فیش هنوز ثبت نشده):\n"]
    for o in rows:
        lines.append(
            f"#{o['id']} — @{o['username']} — {toman(o['total'])} — {o['created_at']}"
        )
    await update.message.reply_text("\n".join(lines))


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    s = db.get_stats()
    text = (
        "📊 آمار فروش B.U.Nou\n\n"
        f"کل فروش (تعداد سفارش تایید‌شده): {s['order_count']}\n"
        f"مجموع فروش به تومان: {toman(s['total_toman'])}\n\n"
        f"پرفروش‌ترین فروشنده: "
        + (f"{s['top_vendor_name']} ({s['top_vendor_code']}) — {toman(s['top_vendor_amount'])}" if s["top_vendor_name"] else "هنوز فروشی با کد فروشنده ثبت نشده")
        + "\n\n"
        f"پرفروش‌ترین محصول: "
        + (f"{s['top_product_name']} — {s['top_product_qty']} عدد" if s["top_product_name"] else "هنوز فروشی ثبت نشده")
    )
    await update.message.reply_text(text)


def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_PRODUCTS: [CallbackQueryHandler(select_products)],
            ASK_VENDOR_CHOICE: [CallbackQueryHandler(ask_vendor_choice)],
            ASK_VENDOR_CODE: [
                CommandHandler("skip", skip_vendor),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_vendor_code),
            ],
            ASK_DISCOUNT_CHOICE: [CallbackQueryHandler(ask_discount_choice)],
            ASK_DISCOUNT_CODE: [
                CommandHandler("skip", skip_discount),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_discount_code),
            ],
            ASK_PROVINCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_province)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_SHIPPING: [CallbackQueryHandler(ask_shipping)],
            CONFIRM: [CallbackQueryHandler(confirm_order)],
            WAIT_RECEIPT: [MessageHandler(filters.PHOTO, receive_receipt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_decision, pattern=r"^(approve|reject):\d+$"))

    app.add_handler(CommandHandler("admin_help", admin_help))
    app.add_handler(CommandHandler("add_product", add_product_cmd))
    app.add_handler(CommandHandler("list_products", list_products_cmd))
    app.add_handler(CommandHandler("remove_product", remove_product_cmd))
    app.add_handler(CommandHandler("set_price", set_price_cmd))
    app.add_handler(CommandHandler("add_vendor", add_vendor_cmd))
    app.add_handler(CommandHandler("list_vendors", list_vendors_cmd))
    app.add_handler(CommandHandler("add_discount", add_discount_cmd))
    app.add_handler(CommandHandler("pending_orders", pending_orders_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))

    log.info("Bot starting (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
