TEXTS = {
    "ru": {
        "start": "👋 Добро пожаловать в сервис Vexo!\n\nЯ помогу вам:\n\n📥 Скачать видео и посты без водяного знака с Инстаграм, Тикток и Ютуба - просто отправьте ссылку 🔗\n\n🔍 Найти любимые треки по медиа или тексту - отправьте видео 🎥, аудио 🔊 или напишите название, текст ✏️",
        "error": "⚠️ Видео недоступно, попробуйте снова",
        "loading": "⏳",
        "caption": "✅ Скачано через @Vexoapp_bot",
    },

    "uz": {
        "start": "👋 Vexo servisiga xush kelibsiz!\n\nMen sizga quyidagilarda yordam beraman:\n\n📥 Instagram, Tiktok va Youtube dan video va postlar yuklashda - shunchaki havolani yuboring 🔗\n\n🔍 Sevimli musiqangizni media yoki matn orqali izlashda - video 🎥, audio 🔊 yuboring yoki nomini, matnini yozing  ✏️",
        "error": "⚠️ Video yuklab bo‘lmadi, qayta urinib ko‘ring",
        "loading": "⏳",
        "caption": "✅ @Vexoapp_bot orqali yuklandi",
    }
}


def t(lang, key):
    return TEXTS.get(lang, TEXTS["ru"]).get(key, key)
