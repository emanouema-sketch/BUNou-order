"""
فرآیند کامل ثبت سفارش — هم برای «مشتری عادی» و هم برای «فروشنده‌ای که برای
مشتری خودش سفارش ثبت می‌کند» استفاده می‌شود.

اگر context.user_data["acting_seller_code"] از قبل مقداردهی شده باشد
(یعنی یک فروشنده وارد شده و «ثبت سفارش مشتری» را زده)، مرحله «کد فروشنده
دارید؟» به‌طور کامل رد می‌شود و کد همان فروشنده خودکار به سفارش وصل می‌شود.
"""
import config
import db
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from locations import CITIES, PROVINCES, OTHER_CITY_LABEL
from shipping import get_shipping_options, get_option
from utils import toman, is_valid_phone, clean_digits

(
    SELECT_PRODUCTS, ASK_BUYER_NAME, ASK_SELLER_CHOICE, ASK_SELLER_CODE,
    ASK_DISCOUNT_CHOICE, ASK_DISCOUNT_CODE, ASK_PROVINCE, ASK_CITY,
    ASK_PHONE, ASK_ADDRESS, ASK_SHIPPING, CONFIRM, WAIT_RECEIPT,
) = range(13)


# ---------------------------------------------------------------- helpers
def cart_lines(cart):
    lines, total = [], 0
    for pid, qty in cart.items():
        p = db.get_product(pid)
        if not p:
            continue
        line_total = p["price"] * qty
        total += line_total
        lines.append(f"• {p['name']} × {qty} = {toman(line_total)}")
    return lines, total


def cart_text(cart):
    lines, total = cart_lines(cart)
    if not lines:
        return "سبد خرید خالی است."
    return "\n".join(lines) + f"\n\nجمع کالاها: {toman(total)}"


def cart_subtotal(cart):
    _, total = cart_lines(cart)
    return total


def products_keyboard(cart):
    rows = []
    for p in db.list_products(active_only=True):
        if p["stock"] <= 0:
            continue
        qty = cart.get(p["id"], 0)
        label = f"{p['name']} — {toman(p['price'])}" + (f"  (در سبد: {qty})" if qty else "")
        rows.append([InlineKeyboardButton(label, callback_data=f"add:{p['id']}")])
    rows.append([InlineKeyboardButton("👁 مشاهده جزئیات محصول", callback_data="details")])
    rows.append([InlineKeyboardButton("✅ پایان انتخاب / ادامه", callback_data="done")])
    return InlineKeyboardMarkup(rows)


def details_keyboard():
    rows = []
    for p in db.list_products(active_only=True):
        rows.append([InlineKeyboardButton(p["name"], callback_data=f"detail:{p['id']}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="back_to_products")])
    return InlineKeyboardMarkup(rows)


async def _sync_draft(context, order_id, **fields):
    """آپدیت رکورد سفارش پیش‌نویس در دیتابیس (برای ردیابی سفارش‌های ناقص)."""
    db.update_order(order_id, **fields)


def _schedule_abandon_check(context: ContextTypes.DEFAULT_TYPE, order_id: int):
    if context.job_queue is None:
        return
    context.job_queue.run_once(
        _abandon_check_job, when=config.ABANDON_SECONDS, data={"order_id": order_id}, name=f"abandon_{order_id}"
    )


async def _abandon_check_job(context: ContextTypes.DEFAULT_TYPE):
    order_id = context.job.data["order_id"]
    order = db.get_order(order_id)
    if not order:
        return
    if order["status"] in ("confirmed", "rejected", "waiting_review"):
        return
    if order["abandoned_notified"]:
        return
    db.mark_abandoned_notified(order_id)
    if not config.ADMIN_CHAT_ID:
        return
    seller_line = f"کد فروشنده: {order['seller_code']}\n" if order["seller_code"] else ""
    phone_line = f"تلفن: {order['phone']}\n" if order["phone"] else ""
    text = (
        f"⚠️ سفارش رهاشده #{order_id}\n\n"
        f"مشتری: @{order['customer_username'] or '—'}\n"
        f"{phone_line}"
        f"محصولات:\n{order['items_text'] or '(هنوز محصولی انتخاب نشده)'}\n"
        f"مبلغ تقریبی: {toman(order['subtotal'])}\n"
        f"{seller_line}"
        f"مرحله‌ای که متوقف شده: {order['stage']}\n"
        f"زمان شروع: {order['created_at']}"
    )
    await context.bot.send_message(config.ADMIN_CHAT_ID, text)


# ---------------------------------------------------------------- entry
async def enter_order_flow(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    """نقطه ورود مشترک؛ هم از دستور مستقیم مشتری و هم از دکمه فروشنده صدا زده می‌شود."""
    if isinstance(update_or_query, Update) and update_or_query.message:
        chat_id = update_or_query.effective_chat.id
        username = update_or_query.effective_user.username or update_or_query.effective_user.first_name
        send = update_or_query.message.reply_text
    else:
        query = update_or_query
        chat_id = query.message.chat.id
        username = query.from_user.username or query.from_user.first_name
        send = query.message.reply_text

    context.user_data["cart"] = {}
    order_id = db.create_draft_order(chat_id, username)
    context.user_data["order_id"] = order_id
    _schedule_abandon_check(context, order_id)

    await send(
        "🛍 به فروشگاه NouNilla خوش آمدید!\n"
        "روی هر محصول بزنید تا به سبد اضافه شود (چند بار بزنید برای تعداد بیشتر).\n"
        "برای دیدن عکس/توضیحات هر کالا، «مشاهده جزئیات محصول» را بزنید."
    )
    await send(cart_text(context.user_data["cart"]), reply_markup=products_keyboard(context.user_data["cart"]))
    return SELECT_PRODUCTS


async def start_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["acting_seller_code"] = None
    return await enter_order_flow(update, context)


async def start_customer_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورودی مسیر «👤 خرید به عنوان مشتری» از منوی اصلی (دکمه، نه دستور)."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data["acting_seller_code"] = None
    return await enter_order_flow(query, context)


# ---------------------------------------------------------------- products
async def select_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart = context.user_data.setdefault("cart", {})
    order_id = context.user_data["order_id"]

    if query.data == "details":
        await query.edit_message_text("برای دیدن جزئیات، یک محصول را انتخاب کنید:", reply_markup=details_keyboard())
        return SELECT_PRODUCTS

    if query.data == "back_to_products":
        await query.edit_message_text(cart_text(cart), reply_markup=products_keyboard(cart))
        return SELECT_PRODUCTS

    if query.data.startswith("detail:"):
        pid = int(query.data.split(":")[1])
        p = db.get_product(pid)
        if not p:
            await query.answer("این محصول موجود نیست.", show_alert=True)
            return SELECT_PRODUCTS
        caption = f"🏷 {p['name']}\n\n{p['description']}\n\n💰 {toman(p['price'])}\nموجودی: {p['stock']} عدد"
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_products")]])
        if p["photo_file_id"]:
            await query.message.reply_photo(p["photo_file_id"], caption=caption, reply_markup=back_kb)
        else:
            await query.message.reply_text(caption, reply_markup=back_kb)
        return SELECT_PRODUCTS

    if query.data == "done":
        if not cart:
            await query.answer("سبد خرید خالی است.", show_alert=True)
            return SELECT_PRODUCTS
        items_text = "\n".join(cart_lines(cart)[0])
        await _sync_draft(context, order_id, items_text=items_text, subtotal=cart_subtotal(cart), stage="نام خریدار")
        await query.edit_message_text(cart_text(cart))
        await query.message.reply_text("نام خریدار را وارد کنید:")
        return ASK_BUYER_NAME

    pid = int(query.data.split(":")[1])
    product = db.get_product(pid)
    if not product or product["stock"] <= cart.get(pid, 0):
        await query.answer("موجودی این محصول کافی نیست.", show_alert=True)
        return SELECT_PRODUCTS
    cart[pid] = cart.get(pid, 0) + 1
    items_text = "\n".join(cart_lines(cart)[0])
    await _sync_draft(context, order_id, items_text=items_text, subtotal=cart_subtotal(cart))
    await query.edit_message_text(cart_text(cart), reply_markup=products_keyboard(cart))
    return SELECT_PRODUCTS


# ---------------------------------------------------------------- buyer name
async def ask_buyer_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["buyer_name"] = name
    order_id = context.user_data["order_id"]
    await _sync_draft(context, order_id, buyer_name=name, stage="کد فروشنده")

    acting_seller_code = context.user_data.get("acting_seller_code")
    if acting_seller_code:
        # فروشنده خودش سفارش می‌زند؛ نیازی به پرسیدن کد نیست
        context.user_data["seller_code"] = acting_seller_code
        await _sync_draft(context, order_id, seller_code=acting_seller_code)
        return await ask_discount_entry(update.message, context)

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("بله، کد فروشنده دارم", callback_data="seller_yes"),
          InlineKeyboardButton("خیر", callback_data="seller_no")]]
    )
    await update.message.reply_text("آیا کد فروشنده دارید؟", reply_markup=keyboard)
    return ASK_SELLER_CHOICE


# ---------------------------------------------------------------- seller code
async def ask_seller_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "seller_no":
        context.user_data["seller_code"] = None
        return await ask_discount_entry(query.message, context)
    await query.edit_message_text("کد فروشنده را وارد کنید:")
    return ASK_SELLER_CODE


async def ask_seller_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    seller = db.get_seller_by_code(code)
    if not seller or not seller["active"]:
        await update.message.reply_text("این کد فروشنده معتبر نیست. دوباره وارد کنید یا /skip را بزنید.")
        return ASK_SELLER_CODE
    context.user_data["seller_code"] = code
    await _sync_draft(context, context.user_data["order_id"], seller_code=code)
    await update.message.reply_text(f"کد فروشنده «{code}» ثبت شد. ✅")
    return await ask_discount_entry(update.message, context)


async def skip_seller_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["seller_code"] = None
    return await ask_discount_entry(update.message, context)


# ---------------------------------------------------------------- discount
async def ask_discount_entry(message, context: ContextTypes.DEFAULT_TYPE):
    await _sync_draft(context, context.user_data["order_id"], stage="کد تخفیف")
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
    await _sync_draft(context, context.user_data["order_id"], discount_code=code, discount_amount=amount)
    await update.message.reply_text(f"کد تخفیف «{code}» ({disc['percent']}٪) اعمال شد. ✅ تخفیف: {toman(amount)}")
    return await ask_province_entry(update.message, context)


async def skip_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["discount_code"] = None
    context.user_data["discount_amount"] = 0
    return await ask_province_entry(update.message, context)


# ---------------------------------------------------------------- province/city
async def ask_province_entry(message, context: ContextTypes.DEFAULT_TYPE):
    await _sync_draft(context, context.user_data["order_id"], stage="انتخاب استان")
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
    await _sync_draft(context, context.user_data["order_id"], province=province, stage="انتخاب شهر")

    cities = CITIES[province] + [OTHER_CITY_LABEL]
    rows = [cities[i:i + 2] for i in range(0, len(cities), 2)]
    keyboard = ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"شهر خود را در استان {province} انتخاب کنید:", reply_markup=keyboard)
    return ASK_CITY


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if context.user_data.get("manual_city_mode"):
        context.user_data["city"] = text
        context.user_data["manual_city_mode"] = False
        return await ask_phone_entry(update, context)

    if text == OTHER_CITY_LABEL:
        context.user_data["manual_city_mode"] = True
        await update.message.reply_text("نام شهر خود را تایپ کنید:", reply_markup=ReplyKeyboardRemove())
        return ASK_CITY

    province = context.user_data.get("province")
    if province and text not in CITIES.get(province, []):
        await update.message.reply_text("لطفا یکی از شهرهای نمایش داده‌شده را انتخاب کنید، یا «شهر دیگر» را بزنید.")
        return ASK_CITY

    context.user_data["city"] = text
    return await ask_phone_entry(update, context)


# ---------------------------------------------------------------- phone
async def ask_phone_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _sync_draft(context, context.user_data["order_id"], city=context.user_data["city"], stage="شماره تلفن")
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 ارسال شماره تماس من", request_contact=True)]],
        one_time_keyboard=True, resize_keyboard=True,
    )
    await update.message.reply_text(
        "شماره تلفن تماس را با دکمه زیر ارسال کنید، یا مستقیم تایپ کنید (مثلا 09123456789):",
        reply_markup=keyboard,
    )
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = clean_digits(update.message.contact.phone_number)
    else:
        phone = clean_digits(update.message.text or "")

    if not phone or len(phone) < 10:
        await update.message.reply_text("شماره تلفن معتبر به نظر نمی‌رسد. دوباره ارسال کنید:")
        return ASK_PHONE

    context.user_data["phone"] = phone
    await _sync_draft(context, context.user_data["order_id"], phone=phone, stage="آدرس دقیق")
    await update.message.reply_text("آدرس دقیق (خیابان، پلاک، واحد) را بنویسید:", reply_markup=ReplyKeyboardRemove())
    return ASK_ADDRESS


# ---------------------------------------------------------------- address + shipping
async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    context.user_data["address"] = address
    await _sync_draft(context, context.user_data["order_id"], address=address, stage="روش ارسال")

    province = context.user_data["province"]
    options = get_shipping_options(province)
    buttons = []
    for opt in options:
        label = opt["label"] if opt["cod"] else f"{opt['label']} — {toman(opt['cost'])}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"ship:{opt['method']}")])
    await update.message.reply_text("روش ارسال را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_SHIPPING


async def ask_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split(":")[1]
    province = context.user_data["province"]
    option = get_option(province, method)

    context.user_data["shipping_method"] = method
    context.user_data["shipping_cost"] = option["cost"]
    context.user_data["shipping_cod"] = option["cod"]

    cart = context.user_data["cart"]
    subtotal = cart_subtotal(cart)
    discount_amount = context.user_data.get("discount_amount", 0)
    total = subtotal - discount_amount + option["cost"]
    context.user_data["subtotal"] = subtotal
    context.user_data["total"] = total

    order_id = context.user_data["order_id"]
    await _sync_draft(
        context, order_id,
        shipping_method=method, shipping_cost=option["cost"], shipping_cod=int(option["cod"]),
        total=total, stage="تایید نهایی سفارش",
    )

    ship_line = f"روش ارسال: {option['label']}"
    ship_line += " — هزینه در محل تحویل، نقدی از گیرنده دریافت می‌شود." if option["cod"] else f" ({toman(option['cost'])})"

    summary = (
        cart_text(cart) + "\n\n"
        f"خریدار: {context.user_data.get('buyer_name')}\n"
        f"کد فروشنده: {context.user_data.get('seller_code') or 'ندارد'}\n"
        f"کد تخفیف: {context.user_data.get('discount_code') or 'ندارد'}"
        + (f" (- {toman(discount_amount)})" if discount_amount else "") + "\n"
        f"{ship_line}\n"
        f"استان/شهر: {province} / {context.user_data['city']}\n"
        f"آدرس: {context.user_data['address']}\n"
        f"تلفن: {context.user_data['phone']}\n\n"
        f"💰 مبلغ قابل پرداخت آنلاین: {toman(total)}"
        + ("\n(هزینه پیک جدا و نقدی است)" if option["cod"] else "")
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ تایید و ادامه به پرداخت", callback_data="confirm"),
          InlineKeyboardButton("❌ انصراف", callback_data="cancel")]]
    )
    await query.edit_message_text(summary, reply_markup=keyboard)
    return CONFIRM


# ---------------------------------------------------------------- confirm + payment
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = context.user_data["order_id"]

    if query.data == "cancel":
        db.set_status(order_id, "abandoned")
        await query.edit_message_text("سفارش لغو شد. برای شروع دوباره /start را بزنید.")
        return ConversationHandler.END

    d = context.user_data
    cart = d["cart"]
    items = []
    for pid, qty in cart.items():
        p = db.get_product(pid)
        items.append({"product_id": pid, "name": p["name"], "qty": qty, "price": p["price"]})
    db.finalize_items(order_id, items)
    db.update_order(order_id, status="pending_payment", stage="در انتظار پرداخت")

    await query.edit_message_text(
        f"سفارش شما با شماره #{order_id} ثبت شد.\n\n"
        f"لطفا مبلغ {toman(d['total'])} را به شماره کارت زیر واریز کنید:\n\n"
        f"💳 {config.CARD_NUMBER}\n👤 به نام: {config.CARD_HOLDER_NAME}\n\n"
        "سپس عکس رسید یا فیش واریزی را همین‌جا ارسال کنید."
    )

    if config.ADMIN_CHAT_ID:
        await context.bot.send_message(
            config.ADMIN_CHAT_ID,
            f"🕐 سفارش #{order_id} ثبت شد و در انتظار پرداخت است.\n"
            f"خریدار: {d.get('buyer_name')}\nمبلغ: {toman(d['total'])}\n"
            f"برای دیدن سفارش‌های ناقص: /nouh95",
        )
    return WAIT_RECEIPT


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("لطفا تصویر فیش واریزی را ارسال کنید.")
        return WAIT_RECEIPT

    order_id = context.user_data["order_id"]
    file_id = update.message.photo[-1].file_id
    db.attach_receipt(order_id, file_id)
    order = db.get_order(order_id)

    await update.message.reply_text("فیش شما دریافت شد. ✅ پس از تایید مدیر، نتیجه را همین‌جا اطلاع می‌دهیم.")

    if config.ADMIN_CHAT_ID:
        seller = db.get_seller_by_code(order["seller_code"]) if order["seller_code"] else None
        option = get_option(order["province"], order["shipping_method"])
        ship_label = option["label"] if option else order["shipping_method"]
        caption = (
            f"🧾 سفارش #{order_id} — در انتظار بررسی\n\n"
            f"خریدار: {order['buyer_name']}\n"
            f"یوزرنیم: @{order['customer_username'] or '—'}\n"
            f"تلفن: {order['phone']}\n\n"
            f"محصولات:\n{order['items_text']}\n\n"
            f"مبلغ کالاها: {toman(order['subtotal'])}\n"
            f"کد فروشنده: {order['seller_code'] or 'ندارد'}" + (f" ({seller['name']})" if seller else "") + "\n"
            f"کد تخفیف: {order['discount_code'] or 'ندارد'}" + (f" (- {toman(order['discount_amount'])})" if order["discount_amount"] else "") + "\n"
            f"استان: {order['province']}\nشهر: {order['city']}\nآدرس: {order['address']}\n"
            f"روش ارسال: {ship_label}" + (" (پس‌کرایه)" if order["shipping_cod"] else f" ({toman(order['shipping_cost'])})") + "\n\n"
            f"💰 مبلغ نهایی: {toman(order['total'])}\n"
            f"وضعیت: در انتظار تایید"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ تایید سفارش", callback_data=f"approve:{order_id}"),
              InlineKeyboardButton("❌ رد سفارش", callback_data=f"reject:{order_id}")]]
        )
        await context.bot.send_photo(config.ADMIN_CHAT_ID, photo=file_id, caption=caption, reply_markup=keyboard)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("order_id")
    if order_id:
        db.set_status(order_id, "abandoned")
    await update.message.reply_text("عملیات لغو شد. برای شروع دوباره /start را بزنید.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def build_conversation_handler(entry_points):
    return ConversationHandler(
        entry_points=entry_points,
        states={
            SELECT_PRODUCTS: [CallbackQueryHandler(select_products)],
            ASK_BUYER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_buyer_name)],
            ASK_SELLER_CHOICE: [CallbackQueryHandler(ask_seller_choice)],
            ASK_SELLER_CODE: [
                CommandHandler("skip", skip_seller_code),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_seller_code),
            ],
            ASK_DISCOUNT_CHOICE: [CallbackQueryHandler(ask_discount_choice)],
            ASK_DISCOUNT_CODE: [
                CommandHandler("skip", skip_discount),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_discount_code),
            ],
            ASK_PROVINCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_province)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            ASK_PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, ask_phone)],
            ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASK_SHIPPING: [CallbackQueryHandler(ask_shipping)],
            CONFIRM: [CallbackQueryHandler(confirm_order)],
            WAIT_RECEIPT: [MessageHandler(filters.PHOTO, receive_receipt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="order_flow",
        persistent=False,
    )
