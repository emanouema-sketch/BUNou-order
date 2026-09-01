"""
پنل مدیریت — دسترسی فقط با دستور مخفی (از ENV: ADMIN_COMMAND) و فقط برای
Chat ID برابر با ADMIN_CHAT_ID. صرفاً دانستن نام دستور کافی نیست.

بخش زیادی از عملیات (فعال/غیرفعال، حذف) با دکمه انجام می‌شود؛ ویرایش‌های
متنی (قیمت، موجودی، توضیح) با دستورهای کوتاه که همین‌جا مستند شده‌اند —
این ترکیب باعث می‌شود پنل هم ساده بماند هم کامل باشد.
"""
import config
import db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from utils import toman
from order_flow import get_option


def is_admin_update(update: Update) -> bool:
    return bool(config.ADMIN_CHAT_ID) and str(update.effective_chat.id) == str(config.ADMIN_CHAT_ID)


async def _guard(query) -> bool:
    if not (config.ADMIN_CHAT_ID and str(query.message.chat.id) == str(config.ADMIN_CHAT_ID)):
        await query.answer("دسترسی ندارید.", show_alert=True)
        return False
    await query.answer()
    return True


def main_admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 محصولات", callback_data="adm_products"),
         InlineKeyboardButton("🧾 سفارش‌ها", callback_data="adm_orders")],
        [InlineKeyboardButton("👨‍💼 فروشنده‌ها", callback_data="adm_sellers"),
         InlineKeyboardButton("🎟️ تخفیف‌ها", callback_data="adm_discounts")],
        [InlineKeyboardButton("📊 گزارش", callback_data="adm_report")],
    ])


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return  # حتی جواب هم نمی‌دهیم که وجود این دستور لو نرود
    await update.message.reply_text("👨‍💻 پنل مدیریت NouNilla", reply_markup=main_admin_kb())


async def adm_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    await query.edit_message_text("👨‍💻 پنل مدیریت NouNilla", reply_markup=main_admin_kb())


# ==================== محصولات ====================
async def adm_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    rows = db.list_products()
    lines = ["📦 محصولات:\n"]
    kb = []
    for p in rows:
        status = "🟢" if p["active"] else "🔴"
        lines.append(f"#{p['id']} {status} {p['name']} — {toman(p['price'])} — موجودی: {p['stock']}")
        kb.append([
            InlineKeyboardButton(("غیرفعال کردن" if p["active"] else "فعال کردن") + f" #{p['id']}", callback_data=f"adm_p_tog:{p['id']}"),
            InlineKeyboardButton(f"🗑 حذف #{p['id']}", callback_data=f"adm_p_del:{p['id']}"),
        ])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")])
    lines.append(
        "\nدستورهای مدیریت محصول:\n"
        "/addproduct نام|قیمت|موجودی|توضیح\n"
        "/setprice شناسه|قیمت_جدید\n"
        "/setstock شناسه|موجودی_جدید\n"
        "/setdesc شناسه|توضیح_جدید\n"
        "/setphoto شناسه  (بعد از این دستور، عکس محصول را بفرستید)"
    )
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def adm_p_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    pid = int(query.data.split(":")[1])
    db.toggle_product_active(pid)
    await adm_products(update, context)


async def adm_p_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    pid = int(query.data.split(":")[1])
    db.remove_product(pid)
    await adm_products(update, context)


async def addproduct_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        name, price, stock, desc = update.message.text.split(" ", 1)[1].split("|")
        pid = db.add_product(name.strip(), int(price.strip()), int(stock.strip()), desc.strip())
        await update.message.reply_text(f"محصول «{name.strip()}» با شناسه #{pid} اضافه شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /addproduct نام|قیمت|موجودی|توضیح")


async def setprice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        pid, price = update.message.text.split(" ", 1)[1].split("|")
        db.update_product_field(int(pid.strip()), "price", int(price.strip()))
        await update.message.reply_text("قیمت به‌روزرسانی شد. ✅")
    except Exception:
        await update.message.reply_text("فرمت درست: /setprice شناسه|قیمت_جدید")


async def setstock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        pid, stock = update.message.text.split(" ", 1)[1].split("|")
        db.update_product_field(int(pid.strip()), "stock", int(stock.strip()))
        await update.message.reply_text("موجودی به‌روزرسانی شد. ✅")
    except Exception:
        await update.message.reply_text("فرمت درست: /setstock شناسه|موجودی_جدید")


async def setdesc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        pid, desc = update.message.text.split(" ", 1)[1].split("|", 1)
        db.update_product_field(int(pid.strip()), "description", desc.strip())
        await update.message.reply_text("توضیحات به‌روزرسانی شد. ✅")
    except Exception:
        await update.message.reply_text("فرمت درست: /setdesc شناسه|توضیح_جدید")


async def setphoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        pid = int(update.message.text.split(" ", 1)[1].strip())
        context.user_data["awaiting_photo_for_product"] = pid
        await update.message.reply_text(f"حالا عکس محصول #{pid} را ارسال کنید.")
    except Exception:
        await update.message.reply_text("فرمت درست: /setphoto شناسه")


async def admin_receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    pid = context.user_data.pop("awaiting_photo_for_product", None)
    if not pid:
        return
    file_id = update.message.photo[-1].file_id
    db.update_product_field(pid, "photo_file_id", file_id)
    await update.message.reply_text(f"عکس محصول #{pid} ذخیره شد. ✅")


# ==================== فروشنده‌ها ====================
async def adm_sellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    rows = db.list_sellers()
    lines = ["👨‍💼 فروشنده‌ها:\n"]
    kb = []
    for s in rows:
        status = "🟢" if s["active"] else "🔴"
        bound = "متصل" if s["chat_id"] else "هنوز وارد نشده"
        lines.append(f"#{s['id']} {status} {s['name']} — کد: {s['code']} — پورسانت: {s['commission_percent']}٪ — {bound}")
        kb.append([
            InlineKeyboardButton(("غیرفعال" if s["active"] else "فعال") + f" #{s['id']}", callback_data=f"adm_s_tog:{s['id']}"),
            InlineKeyboardButton(f"🗑 حذف #{s['id']}", callback_data=f"adm_s_del:{s['id']}"),
        ])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")])
    lines.append(
        "\nدستورهای مدیریت فروشنده:\n"
        "/addseller نام|کد|درصد_پورسانت\n"
        "/setcommission کد|درصد_جدید"
    )
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def adm_s_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    sid = int(query.data.split(":")[1])
    db.toggle_seller_active(sid)
    await adm_sellers(update, context)


async def adm_s_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    sid = int(query.data.split(":")[1])
    db.remove_seller(sid)
    await adm_sellers(update, context)


async def addseller_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        name, code, rate = update.message.text.split(" ", 1)[1].split("|")
        db.add_seller(name.strip(), code.strip(), float(rate.strip()))
        await update.message.reply_text(f"فروشنده «{name.strip()}» با کد {code.strip().upper()} اضافه شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /addseller نام|کد|درصد_پورسانت")


async def setcommission_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        code, rate = update.message.text.split(" ", 1)[1].split("|")
        seller = db.get_seller_by_code(code.strip())
        if not seller:
            await update.message.reply_text("این کد فروشنده پیدا نشد.")
            return
        db.update_seller_field(seller["id"], "commission_percent", float(rate.strip()))
        await update.message.reply_text("درصد پورسانت به‌روزرسانی شد. ✅")
    except Exception:
        await update.message.reply_text("فرمت درست: /setcommission کد|درصد_جدید")


# ==================== تخفیف‌ها ====================
async def adm_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    rows = db.list_discounts()
    lines = ["🎟️ کدهای تخفیف:\n"]
    kb = []
    for d in rows:
        status = "🟢" if d["active"] else "🔴"
        seller_part = f" — مخصوص فروشنده {d['seller_code']}" if d["seller_code"] else ""
        lines.append(f"{status} {d['code']} — {d['percent']}٪{seller_part}")
        kb.append([
            InlineKeyboardButton(("غیرفعال" if d["active"] else "فعال") + f" {d['code']}", callback_data=f"adm_d_tog:{d['code']}"),
            InlineKeyboardButton(f"🗑 حذف {d['code']}", callback_data=f"adm_d_del:{d['code']}"),
        ])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")])
    lines.append("\nافزودن کد جدید:\n/adddiscount کد|درصد|کد_فروشنده(اختیاری)")
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def adm_d_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    code = query.data.split(":", 1)[1]
    db.toggle_discount(code)
    await adm_discounts(update, context)


async def adm_d_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    code = query.data.split(":", 1)[1]
    db.remove_discount(code)
    await adm_discounts(update, context)


async def adddiscount_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        parts = update.message.text.split(" ", 1)[1].split("|")
        code, percent = parts[0].strip(), int(parts[1].strip())
        seller_code = parts[2].strip() if len(parts) > 2 else None
        db.add_discount(code, percent, seller_code)
        await update.message.reply_text(f"کد تخفیف «{code.upper()}» ({percent}٪) فعال شد.")
    except Exception:
        await update.message.reply_text("فرمت درست: /adddiscount کد|درصد|کد_فروشنده(اختیاری)")


# ==================== سفارش‌ها ====================
def _orders_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("در انتظار پرداخت", callback_data="adm_o_status:pending_payment"),
         InlineKeyboardButton("در انتظار بررسی", callback_data="adm_o_status:waiting_review")],
        [InlineKeyboardButton("تایید‌شده", callback_data="adm_o_status:confirmed"),
         InlineKeyboardButton("ردشده", callback_data="adm_o_status:rejected")],
        [InlineKeyboardButton("ناقص/رهاشده", callback_data="adm_o_status:abandoned")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")],
    ])


async def adm_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    await query.edit_message_text(
        "🧾 سفارش‌ها — یک وضعیت را انتخاب کنید، یا برای جستجو بفرستید:\n/order شماره_سفارش",
        reply_markup=_orders_kb(),
    )


async def adm_orders_by_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    status = query.data.split(":", 1)[1]
    rows = db.orders_by_status(status)
    if not rows:
        text = "سفارشی در این وضعیت نیست."
    else:
        lines = [f"#{o['id']} — {o['buyer_name'] or o['customer_username'] or '—'} — {toman(o['total'])} — {o['created_at']}" for o in rows]
        text = f"سفارش‌های «{status}»:\n\n" + "\n".join(lines) + "\n\nبرای جزئیات کامل: /order شماره_سفارش"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="adm_orders")]])
    await query.edit_message_text(text, reply_markup=kb)


async def order_search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_update(update):
        return
    try:
        order_id = int(update.message.text.split(" ", 1)[1].strip())
    except Exception:
        await update.message.reply_text("فرمت درست: /order شماره_سفارش")
        return
    o = db.search_order(order_id)
    if not o:
        await update.message.reply_text("سفارشی با این شماره پیدا نشد.")
        return
    option = get_option(o["province"], o["shipping_method"]) if o["shipping_method"] else None
    ship_label = option["label"] if option else (o["shipping_method"] or "—")
    text = (
        f"🧾 سفارش #{o['id']}\n\n"
        f"وضعیت: {o['status']} (مرحله: {o['stage']})\n"
        f"خریدار: {o['buyer_name'] or '—'}\n"
        f"یوزرنیم: @{o['customer_username'] or '—'}\n"
        f"تلفن: {o['phone'] or '—'}\n\n"
        f"محصولات:\n{o['items_text'] or '—'}\n\n"
        f"جمع کالاها: {toman(o['subtotal'])}\n"
        f"کد فروشنده: {o['seller_code'] or 'ندارد'}\n"
        f"کد تخفیف: {o['discount_code'] or 'ندارد'}\n"
        f"استان/شهر: {o['province'] or '—'} / {o['city'] or '—'}\n"
        f"آدرس: {o['address'] or '—'}\n"
        f"روش ارسال: {ship_label}\n"
        f"مبلغ نهایی: {toman(o['total'])}\n"
        f"ایجاد شده: {o['created_at']}"
    )
    if o["receipt_file_id"]:
        await update.message.reply_photo(o["receipt_file_id"], caption=text)
    else:
        await update.message.reply_text(text)


# ==================== گزارش ====================
async def adm_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _guard(query):
        return
    t = db.stats_today()
    o = db.stats_overall()
    text = (
        "📊 گزارش فروشگاه\n\n"
        f"سفارش امروز (تایید‌شده): {t['today_order_count']}\n"
        f"فروش امروز: {toman(t['today_sales'])}\n"
        f"در انتظار پرداخت: {t['pending_payment']}\n"
        f"سفارش‌های رهاشده: {t['abandoned']}\n"
        f"کل سفارش‌های تایید‌شده: {t['confirmed_total']}\n\n"
        f"مجموع فروش کل: {toman(o['total_toman'])}\n\n"
        "پرفروش‌ترین فروشنده: " + (
            f"{o['top_seller_name']} ({o['top_seller_code']}) — {toman(o['top_seller_amount'])}"
            if o["top_seller_name"] else "هنوز فروشی با کد فروشنده نداریم"
        ) + "\n"
        "پرفروش‌ترین محصول: " + (
            f"{o['top_product_name']} — {o['top_product_qty']} عدد" if o["top_product_name"] else "هنوز فروشی نداریم"
        )
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")]])
    await query.edit_message_text(text, reply_markup=kb)


# ==================== تایید/رد سفارش (از پیام فیش) ====================
async def admin_order_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not (config.ADMIN_CHAT_ID and str(query.message.chat.id) == str(config.ADMIN_CHAT_ID)):
        await query.answer("دسترسی ندارید.", show_alert=True)
        return
    await query.answer()
    action, order_id = query.data.split(":")
    order_id = int(order_id)
    order = db.get_order(order_id)
    if not order:
        await query.edit_message_caption(caption="این سفارش پیدا نشد.")
        return

    if action == "approve":
        db.set_status(order_id, "confirmed")
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n✅ تایید شد.")
        await context.bot.send_message(
            order["customer_chat_id"],
            f"سفارش #{order_id} شما تایید و ثبت نهایی شد. ممنون از خرید شما از NouNilla 🌸",
        )
    else:
        db.set_status(order_id, "rejected")
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n❌ رد شد.")
        await context.bot.send_message(
            order["customer_chat_id"],
            f"متاسفانه فیش پرداخت سفارش #{order_id} تایید نشد. لطفا با پشتیبانی تماس بگیرید یا فیش صحیح را دوباره ارسال کنید.",
        )


def register_admin_handlers(app):
    app.add_handler(CommandHandler(config.ADMIN_COMMAND, admin_menu))
    app.add_handler(CallbackQueryHandler(adm_back, pattern="^adm_back$"))

    app.add_handler(CallbackQueryHandler(adm_products, pattern="^adm_products$"))
    app.add_handler(CallbackQueryHandler(adm_p_toggle, pattern=r"^adm_p_tog:\d+$"))
    app.add_handler(CallbackQueryHandler(adm_p_delete, pattern=r"^adm_p_del:\d+$"))
    app.add_handler(CommandHandler("addproduct", addproduct_cmd))
    app.add_handler(CommandHandler("setprice", setprice_cmd))
    app.add_handler(CommandHandler("setstock", setstock_cmd))
    app.add_handler(CommandHandler("setdesc", setdesc_cmd))
    app.add_handler(CommandHandler("setphoto", setphoto_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, admin_receive_photo), group=1)

    app.add_handler(CallbackQueryHandler(adm_sellers, pattern="^adm_sellers$"))
    app.add_handler(CallbackQueryHandler(adm_s_toggle, pattern=r"^adm_s_tog:\d+$"))
    app.add_handler(CallbackQueryHandler(adm_s_delete, pattern=r"^adm_s_del:\d+$"))
    app.add_handler(CommandHandler("addseller", addseller_cmd))
    app.add_handler(CommandHandler("setcommission", setcommission_cmd))

    app.add_handler(CallbackQueryHandler(adm_discounts, pattern="^adm_discounts$"))
    app.add_handler(CallbackQueryHandler(adm_d_toggle, pattern=r"^adm_d_tog:.+$"))
    app.add_handler(CallbackQueryHandler(adm_d_delete, pattern=r"^adm_d_del:.+$"))
    app.add_handler(CommandHandler("adddiscount", adddiscount_cmd))

    app.add_handler(CallbackQueryHandler(adm_orders, pattern="^adm_orders$"))
    app.add_handler(CallbackQueryHandler(adm_orders_by_status, pattern=r"^adm_o_status:.+$"))
    app.add_handler(CommandHandler("order", order_search_cmd))

    app.add_handler(CallbackQueryHandler(adm_report, pattern="^adm_report$"))

    app.add_handler(CallbackQueryHandler(admin_order_decision, pattern=r"^(approve|reject):\d+$"))
