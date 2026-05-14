from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import get_users_count, get_users
from db import (
    get_total_events,
    get_today_events,
    get_success_count,
    get_error_count
)
from db import (
    get_user,
    get_user_total_events,
    get_user_success_events,
    get_user_error_events
)
from db import (
    is_user_banned,
    ban_user,
    unban_user
)

PAGE_SIZE = 10
ADMINS = {1648220477}  # добавляешь свои ID

def build_users_page(page: int):
    user_buttons = []
    offset = page * PAGE_SIZE
    users = get_users(offset, PAGE_SIZE)

    total_users = get_users_count()
    text = f"👥 Users {total_users} (page {page + 1})\n\n"

    keyboard = []
    for i, user in enumerate(users, start=1 + offset):
        user_id, username, first_name, first_seen, last_seen = user
        name = first_name if first_name else (username or "NoName")
        date_text = first_seen.strftime("%y.%m.%d %H:%M")
        link = f"tg://user?id={user_id}"
        text += f'{i}. <a href="{link}">{name}</a> | {user_id} | {date_text}\n'

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
        await update.message.reply_text("⛔ Admin emassiz")
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
    ban_text = "🚫 Бан"
    query = update.callback_query

    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.edit_message_text("⛔ Admin emassiz")
        return

    if query.data == "stats":
        text = (
            "📊 Статистика\n\n"
            f"📥 Общие запросы: {get_total_events()}\n"
            f"📅 Запросы на сегодня: {get_today_events()}\n"
            f"✅ Успехи: {get_success_count()}\n"
            f"❌ Ошибки: {get_error_count()}"
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
    elif query.data.startswith("user:"):
        _, selected_user_id, page = query.data.split(":")
        user = get_user(selected_user_id)
        user_id, username, first_name, first_seen, last_seen = user
        name = first_name or username or "NoName"
        first_seen_text = first_seen.strftime("%y.%m.%d %H:%M")
        last_seen_text = last_seen.strftime("%y.%m.%d %H:%M")
        total = get_user_total_events(selected_user_id)
        success = get_user_success_events(selected_user_id)
        errors = get_user_error_events(selected_user_id)
        link = f"tg://user?id={user_id}"

        text = (
            f'👤 <a href="{link}">{name}</a>\n\n'
            f"🆔 {selected_user_id}\n\n"
            f"📅 Регистрация: {first_seen_text}\n"
            f"🕒 Последняя активность: {last_seen_text}\n\n"
            f"📥 Запросы: {total}\n"
            f"✅ Успехи: {success}\n"
            f"❌ Ошибки: {errors}"
        )
        if is_user_banned(user_id):
            ban_text = "✅ Разбан"
        keyboard = [
            [
                InlineKeyboardButton(
                    ban_text,
                    callback_data=f"ban_{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data=f"users:{page}"
                )
            ]
        ]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    elif query.data.startswith("ban_"):
        target_user_id = int(query.data.split("_")[1])

        if is_user_banned(target_user_id):
            unban_user(target_user_id)
            ban_text = "🚫 Бан"
            alert_text = "✅ Пользователь разбанен"
        else:
            ban_user(target_user_id)
            ban_text = "✅ Разбан"
            alert_text = "🚫 Пользователь забанен"
        keyboard = [
            [
                InlineKeyboardButton(
                    ban_text,
                    callback_data=f"ban_{target_user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="users:0"
                )
            ]
        ]
        await query.answer(alert_text)
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "back":
        await query.edit_message_text(
            "🔐 Admin Panel",
            reply_markup=admin_menu_keyboard()
        )
