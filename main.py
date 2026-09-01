import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import config
import db
import order_flow
import seller
import admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("nounilla")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 خرید به عنوان مشتری", callback_data="main_customer")],
        [InlineKeyboardButton("👨‍💼 ورود به عنوان فروشنده", callback_data="main_seller")],
    ])
    await update.message.reply_text(
        f"سلام! به فروشگاه {config.STORE_NAME} خوش آمدید. 🌸\nیکی از مسیرهای زیر را انتخاب کنید:",
        reply_markup=kb,
    )


def main():
    if not config.BOT_TOKEN:
        raise SystemExit("متغیر BOT_TOKEN تنظیم نشده است.")

    db.init_db()
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))

    # مسیر اصلی خرید — هم برای مشتری عادی و هم برای فروشنده‌ای که برای
    # مشتری‌اش سفارش می‌زند (هر دو نقطه ورود، یک ConversationHandler مشترک‌اند)
    order_conv = order_flow.build_conversation_handler(entry_points=[
        CallbackQueryHandler(order_flow.start_customer_cb, pattern="^main_customer$"),
        CallbackQueryHandler(seller.seller_new_order_entry, pattern="^seller_new_order$"),
    ])
    app.add_handler(order_conv)

    # ورود فروشنده (کد اختصاصی فقط بار اول)
    app.add_handler(seller.build_seller_login_conversation())
    seller.register_seller_menu_handlers(app)

    # پنل مدیریت
    admin.register_admin_handlers(app)

    log.info("NouNilla bot starting (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
