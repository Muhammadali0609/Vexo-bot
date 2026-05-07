from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import get_users_count
from db import (
    get_total_events,
    get_today_events,
    get_success_count,
    get_error_count
)

ADMINS = {1648220477}  # добавляешь свои ID

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


async def adminm(update, context):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Access denied")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("👤 Пользователи", callback_data="users")],
    ]

    await update.message.reply_text(
        "🔐 Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_callback(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.edit_message_text("⛔ No access")
        return

    if query.data == "stats":
        text = (
            "📊 Statistics\n\n"
            f"📥 Total requests: {get_total_events()}\n"
            f"📅 Today: {get_today_events()}\n"
            f"✅ Success: {get_success_count()}\n"
            f"❌ Errors: {get_error_count()}"
        )
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "users":
        await query.edit_message_text("👤 Пользователи системы")