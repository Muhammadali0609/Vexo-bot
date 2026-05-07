from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import get_users_count, get_users
from db import (
    get_total_events,
    get_today_events,
    get_success_count,
    get_error_count
)

PAGE_SIZE = 10
ADMINS = {1648220477}  # добавляешь свои ID

def build_users_page(page: int):
    user_buttons = []
    offset = page * PAGE_SIZE
    users = get_users(offset, PAGE_SIZE)

    text = f"👥 Users (page {page + 1})\n\n"

    keyboard = []
    for i, user in enumerate(users, start=1 + offset):
        user_id, username, first_name = user

        name = first_name if first_name else (username or "NoName")

        link = f"tg://user?id={user_id}"

        text += f'{i}. <a href="{link}">{name}</a> | {user_id}\n'

        user_buttons.append(
            InlineKeyboardButton(
                str(i),
                callback_data=f"user:{user_id}:{page}"
            )
        )

    keyboard.append(user_buttons)

    nav = []

    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"users:{page-1}"))

    nav.append(InlineKeyboardButton("🔍 Search", callback_data="search_users"))

    # если есть ещё пользователи
    if len(users) == PAGE_SIZE:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"users:{page+1}"))

    keyboard.append(nav)

    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    ])

    return text, InlineKeyboardMarkup(keyboard)


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


async def adminm(update, context):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Access denied")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("👤 Пользователи", callback_data="users:0")],
    ]

    await update.message.reply_text(
        "🔐 Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("👤 Пользователи", callback_data="users:0")]
    ])

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
    elif query.data.startswith("users:"):
        page = int(query.data.split(":")[1])
        text, markup = build_users_page(page)
        await query.edit_message_text(
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    elif query.data == "back":
        await query.edit_message_text(
            "🔐 Admin Panel",
            reply_markup=admin_menu_keyboard()
        )