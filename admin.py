from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
        await query.edit_message_text("📊 Статистика системы")

    elif query.data == "users":
        await query.edit_message_text("👤 Пользователи системы")