"""
پنل فروشنده: ورود با کد اختصاصی (فقط بار اول)، سپس تشخیص خودکار بر اساس
Chat ID، به‌علاوه سفارش‌ها/فروش/پورسانت/گزارش خودش.
"""
import db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters
from utils import toman
from order_flow import enter_order_flow

SELLER_ASK_CODE = 100


def seller_menu_markup(seller):
    text = (
        f"👨‍💼 پنل فروشنده — {seller['name']}\n"
        f"کد فروشنده: {seller['code']}\n"
        f"درصد پورسانت: {seller['commission_percent']}٪"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 ثبت سفارش مشتری", callback_data="seller_new_order")],
        [InlineKeyboardButton("📦 سفارش‌های من", callback_data="seller_my_orders")],
        [InlineKeyboardButton("💰 فروش من", callback_data="seller_my_sales")],
        [InlineKeyboardButton("💵 پورسانت من", callback_data="seller_my_commission")],
        [InlineKeyboardButton("📊 گزارش فروش", callback_data="seller_my_report")],
    ])
    return text, kb


async def seller_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    seller = db.get_seller_by_chat_id(query.message.chat.id)
    if seller:
        text, kb = seller_menu_markup(seller)
        await query.edit_message_text(text, reply_markup=kb)
        return ConversationHandler.END
    await query.edit_message_text("برای ورود به پنل فروشنده، کد فروشنده اختصاصی خود را وارد کنید:")
    return SELLER_ASK_CODE


async def seller_ask_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    seller = db.get_seller_by_code(code)
    if not seller or not seller["active"]:
        await update.message.reply_text("کد فروشنده معتبر نیست. دوباره امتحان کنید یا /cancel را بزنید.")
        return SELLER_ASK_CODE
    if seller["chat_id"] and seller["chat_id"] != update.effective_chat.id:
        await update.message.reply_text("این کد قبلا برای حساب دیگری فعال شده. با مدیر تماس بگیرید.")
        return ConversationHandler.END

    db.bind_seller_chat_id(code, update.effective_chat.id)
    seller = db.get_seller_by_code(code)
    await update.message.reply_text(f"خوش آمدید {seller['name']}! ✅")
    text, kb = seller_menu_markup(seller)
    await update.message.reply_text(text, reply_markup=kb)
    return ConversationHandler.END


async def seller_login_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ورود لغو شد. برای شروع دوباره /start را بزنید.")
    return ConversationHandler.END


def build_seller_login_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(seller_entry, pattern="^main_seller$")],
        states={SELLER_ASK_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_ask_code)]},
        fallbacks=[CommandHandler("cancel", seller_login_cancel)],
        name="seller_login",
        persistent=False,
    )


# --------------- ثبت سفارش مشتری (ورود مشترک به order_flow) ---------------
async def seller_new_order_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    seller = db.get_seller_by_chat_id(query.message.chat.id)
    if not seller:
        await query.edit_message_text("ابتدا باید با کد فروشنده وارد پنل شوید. /start را بزنید.")
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["acting_seller_code"] = seller["code"]
    return await enter_order_flow(query, context)


# --------------- زیرمنوهای فروشنده (خارج از کانورسیشن) ---------------
def _back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل فروشنده", callback_data="seller_back")]])


async def seller_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    seller = db.get_seller_by_chat_id(query.message.chat.id)
    if not seller:
        await query.edit_message_text("دسترسی فروشنده یافت نشد.")
        return
    text, kb = seller_menu_markup(seller)
    await query.edit_message_text(text, reply_markup=kb)


async def seller_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    seller = db.get_seller_by_chat_id(query.message.chat.id)
    if not seller:
        await query.edit_message_text("دسترسی فروشنده یافت نشد.")
        return
    rows = db.seller_orders(seller["code"])
    if not rows:
        text = "هنوز سفارشی با کد شما ثبت نشده است."
    else:
        lines = [f"#{o['id']} — {o['status']} — {toman(o['total'])} — {o['created_at']}" for o in rows]
        text = "📦 آخرین سفارش‌های شما:\n\n" + "\n".join(lines)
    await query.edit_message_text(text, reply_markup=_back_kb())


async def seller_my_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    seller = db.get_seller_by_chat_id(query.message.chat.id)
    if not seller:
        await query.edit_message_text("دسترسی فروشنده یافت نشد.")
        return
    s = db.seller_stats(seller["code"])
    text = f"💰 فروش شما\n\nتعداد سفارش تایید‌شده: {s['order_count']}\nمجموع فروش: {toman(s['sales_total'])}"
    await query.edit_message_text(text, reply_markup=_back_kb())


async def seller_my_commission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    seller = db.get_seller_by_chat_id(query.message.chat.id)
    if not seller:
        await query.edit_message_text("دسترسی فروشنده یافت نشد.")
        return
    s = db.seller_stats(seller["code"])
    text = f"💵 پورسانت شما\n\nدرصد پورسانت: {s['commission_rate']}٪\nمجموع پورسانت کسب‌شده: {toman(s['commission_total'])}"
    await query.edit_message_text(text, reply_markup=_back_kb())


async def seller_my_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    seller = db.get_seller_by_chat_id(query.message.chat.id)
    if not seller:
        await query.edit_message_text("دسترسی فروشنده یافت نشد.")
        return
    s = db.seller_stats(seller["code"])
    text = (
        "📊 گزارش فروش شما\n\n"
        f"تعداد سفارش تایید‌شده: {s['order_count']}\n"
        f"مجموع فروش: {toman(s['sales_total'])}\n"
        f"درصد پورسانت: {s['commission_rate']}٪\n"
        f"مجموع پورسانت: {toman(s['commission_total'])}"
    )
    await query.edit_message_text(text, reply_markup=_back_kb())


def register_seller_menu_handlers(app):
    app.add_handler(CallbackQueryHandler(seller_back, pattern="^seller_back$"))
    app.add_handler(CallbackQueryHandler(seller_my_orders, pattern="^seller_my_orders$"))
    app.add_handler(CallbackQueryHandler(seller_my_sales, pattern="^seller_my_sales$"))
    app.add_handler(CallbackQueryHandler(seller_my_commission, pattern="^seller_my_commission$"))
    app.add_handler(CallbackQueryHandler(seller_my_report, pattern="^seller_my_report$"))
