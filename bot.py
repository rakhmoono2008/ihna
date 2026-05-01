import os
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8239199632:AAGF3i4Qsswck4WEhaeLqHNvGBgE1bb2uVw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

# Conversation states
LANGUAGE, CONTACT, REGION, PROBLEM = range(4)

TEXTS = {
    "ru": {
        "welcome": "👋 Добро пожаловать!\n\nЭтот бот предназначен для приёма обращений граждан Узбекистана.\n\nВыберите язык:",
        "choose_contact": "📞 Хотите оставить свой номер телефона?\n\n⚠️ <b>Внимание:</b> Если вы останетесь анонимным, мы не сможем связаться с вами для уточнения деталей или обратной связи.",
        "share_phone": "📱 Поделиться номером",
        "stay_anon": "🙈 Остаться анонимным",
        "anon_warning": "ℹ️ Вы выбрали анонимность. Обращение будет передано, но <b>мы не сможем связаться с вами</b>.",
        "choose_region": "🗺 Выберите ваш регион:",
        "send_problem": "✍️ Теперь опишите вашу проблему.\n\n📝 Напишите текст сообщения.\n📷 Если есть фото или видео — отправьте их <b>по отдельности</b> (сначала файл, потом текст, или наоборот — бот соберёт всё вместе).\n\nКогда закончите — нажмите кнопку <b>«Отправить обращение»</b>.",
        "submit_btn": "✅ Отправить обращение",
        "cancel_btn": "❌ Отмена",
        "thank_you": "✅ <b>Ваше обращение передано!</b>\n\nСпасибо большое за доверие. Мы обязательно рассмотрим вашу проблему.\n\nЧтобы отправить новое обращение — нажмите /start",
        "media_received": "📎 Файл получен. Продолжайте добавлять файлы или напишите текст. Когда готовы — нажмите <b>«Отправить обращение»</b>.",
        "admin_header": "📨 <b>Новое обращение!</b>",
        "region_label": "🗺 Регион",
        "contact_label": "📞 Контакт",
        "anon_label": "Анонимный",
        "message_label": "💬 Сообщение",
        "no_message": "(только медиафайлы)",
        "error": "Произошла ошибка. Попробуйте снова /start",
        "lang_ru": "🇷🇺 Русский",
        "lang_uz": "🇺🇿 O'zbek",
    },
    "uz": {
        "welcome": "👋 Xush kelibsiz!\n\nBu bot O'zbekiston fuqarolarining murojaatlarini qabul qilish uchun mo'ljallangan.\n\nTilni tanlang:",
        "choose_contact": "📞 Telefon raqamingizni qoldirmoqchimisiz?\n\n⚠️ <b>Diqqat:</b> Anonim qolsangiz, biz siz bilan bog'lana olmaymiz.",
        "share_phone": "📱 Raqamni ulashish",
        "stay_anon": "🙈 Anonim qolish",
        "anon_warning": "ℹ️ Siz anonimlikni tanladingiz. Murojaat uzatiladi, lekin <b>biz siz bilan bog'lana olmaymiz</b>.",
        "choose_region": "🗺 Viloyatingizni tanlang:",
        "send_problem": "✍️ Muammongizni tasvirlab bering.\n\n📝 Matn yozing.\n📷 Rasm yoki video bo'lsa — ularni <b>alohida</b> yuboring. Bot hammasini yig'adi.\n\nTayyor bo'lgach — <b>«Murojaatni yuborish»</b> tugmasini bosing.",
        "submit_btn": "✅ Murojaatni yuborish",
        "cancel_btn": "❌ Bekor qilish",
        "thank_you": "✅ <b>Murojaatingiz qabul qilindi!</b>\n\nKatta rahmat. Muammongizni ko'rib chiqamiz.\n\nYangi murojaat uchun — /start",
        "media_received": "📎 Fayl qabul qilindi. Fayllar qo'shishni davom ettiring yoki matn yozing. Tayyor bo'lgach — <b>«Murojaatni yuborish»</b>.",
        "admin_header": "📨 <b>Yangi murojaat!</b>",
        "region_label": "🗺 Viloyat",
        "contact_label": "📞 Kontakt",
        "anon_label": "Anonim",
        "message_label": "💬 Xabar",
        "no_message": "(faqat media fayllar)",
        "error": "Xatolik yuz berdi. Qaytadan urinib ko'ring /start",
        "lang_ru": "🇷🇺 Русский",
        "lang_uz": "🇺🇿 O'zbek",
    }
}

REGIONS = [
    "Тошкент шаҳри / г. Ташкент",
    "Тошкент вилояти / Ташкентская обл.",
    "Самарқанд / Самарканд",
    "Фарғона / Фергана",
    "Андижон / Андижан",
    "Наманган / Наманган",
    "Бухоро / Бухара",
    "Қашқадарё / Кашкадарья",
    "Сурхондарё / Сурхандарья",
    "Хоразм / Хорезм",
    "Навоий / Навои",
    "Жиззах / Джизак",
    "Сирдарё / Сырдарья",
    "Қорақалпоғистон / Каракалпакстан",
]


def get_text(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["ru"]).get(key, "")


def language_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def contact_keyboard(lang: str):
    keyboard = [
        [InlineKeyboardButton(get_text(lang, "share_phone"), callback_data="contact_phone")],
        [InlineKeyboardButton(get_text(lang, "stay_anon"), callback_data="contact_anon")],
    ]
    return InlineKeyboardMarkup(keyboard)


def region_keyboard():
    keyboard = []
    for i in range(0, len(REGIONS), 2):
        row = [InlineKeyboardButton(REGIONS[i], callback_data=f"region_{i}")]
        if i + 1 < len(REGIONS):
            row.append(InlineKeyboardButton(REGIONS[i + 1], callback_data=f"region_{i+1}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def submit_keyboard(lang: str):
    keyboard = [
        [KeyboardButton(get_text(lang, "submit_btn"))],
        [KeyboardButton(get_text(lang, "cancel_btn"))],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        TEXTS["ru"]["welcome"],
        reply_markup=language_keyboard()
    )
    return LANGUAGE


async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    lang = "ru" if query.data == "lang_ru" else "uz"
    context.user_data["lang"] = lang

    await query.edit_message_text(
        get_text(lang, "choose_contact"),
        reply_markup=contact_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    return CONTACT


async def contact_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")

    if query.data == "contact_phone":
        context.user_data["contact_mode"] = "phone"
        phone_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Отправить номер" if lang == "ru" else "📱 Raqam yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await query.edit_message_text(
            "📲 Нажмите кнопку ниже, чтобы поделиться номером:" if lang == "ru"
            else "📲 Raqamni ulashish uchun quyidagi tugmani bosing:",
        )
        await query.message.reply_text("👇", reply_markup=phone_keyboard)
        return REGION
    else:
        context.user_data["contact_mode"] = "anon"
        context.user_data["contact"] = None
        await query.edit_message_text(
            get_text(lang, "anon_warning"),
            parse_mode=ParseMode.HTML
        )
        await query.message.reply_text(
            get_text(lang, "choose_region"),
            reply_markup=region_keyboard()
        )
        return REGION


async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ru")
    phone = update.message.contact.phone_number
    context.user_data["contact"] = phone

    await update.message.reply_text(
        get_text(lang, "choose_region"),
        reply_markup=region_keyboard()
    )
    return REGION


async def region_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")

    region_idx = int(query.data.split("_")[1])
    context.user_data["region"] = REGIONS[region_idx]
    context.user_data["media_ids"] = []
    context.user_data["text_message"] = ""

    await query.edit_message_text(
        f"✅ {REGIONS[region_idx]}"
    )
    await query.message.reply_text(
        get_text(lang, "send_problem"),
        reply_markup=submit_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    return PROBLEM


async def problem_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ru")
    text = update.message.text

    submit_btn = get_text(lang, "submit_btn")
    cancel_btn = get_text(lang, "cancel_btn")

    if text == submit_btn:
        return await submit_report(update, context)
    elif text == cancel_btn:
        await update.message.reply_text("❌", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)
    else:
        context.user_data["text_message"] = text
        return PROBLEM


async def problem_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ru")

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data.setdefault("media_ids", []).append({"type": "photo", "id": file_id})
        if update.message.caption:
            context.user_data["text_message"] = update.message.caption
    elif update.message.video:
        file_id = update.message.video.file_id
        context.user_data.setdefault("media_ids", []).append({"type": "video", "id": file_id})
        if update.message.caption:
            context.user_data["text_message"] = update.message.caption
    elif update.message.document:
        file_id = update.message.document.file_id
        context.user_data.setdefault("media_ids", []).append({"type": "document", "id": file_id})
        if update.message.caption:
            context.user_data["text_message"] = update.message.caption

    await update.message.reply_text(
        get_text(lang, "media_received"),
        parse_mode=ParseMode.HTML
    )
    return PROBLEM


async def submit_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ru")
    region = context.user_data.get("region", "—")
    contact = context.user_data.get("contact")
    text_msg = context.user_data.get("text_message", "")
    media_ids = context.user_data.get("media_ids", [])

    user = update.effective_user
    contact_str = f"+{contact}" if contact else get_text(lang, "anon_label")

    caption = (
        f"{get_text(lang, 'admin_header')}\n\n"
        f"👤 <b>User:</b> {user.full_name} (@{user.username or '—'}) [<code>{user.id}</code>]\n"
        f"{get_text(lang, 'region_label')}: {region}\n"
        f"{get_text(lang, 'contact_label')}: {contact_str}\n"
        f"🌐 Язык: {('Русский' if lang == 'ru' else 'Ozbek')}\n\n"
        f"{get_text(lang, 'message_label')}:\n{text_msg if text_msg else get_text(lang, 'no_message')}"
    )

    targets = []
    if ADMIN_ID:
        targets.append(ADMIN_ID)
    if GROUP_ID:
        targets.append(GROUP_ID)

    for target in targets:
        try:
            if media_ids:
                # Send first media with caption
                first = media_ids[0]
                if first["type"] == "photo":
                    await context.bot.send_photo(target, first["id"], caption=caption, parse_mode=ParseMode.HTML)
                elif first["type"] == "video":
                    await context.bot.send_video(target, first["id"], caption=caption, parse_mode=ParseMode.HTML)
                elif first["type"] == "document":
                    await context.bot.send_document(target, first["id"], caption=caption, parse_mode=ParseMode.HTML)

                # Send remaining media
                for m in media_ids[1:]:
                    if m["type"] == "photo":
                        await context.bot.send_photo(target, m["id"])
                    elif m["type"] == "video":
                        await context.bot.send_video(target, m["id"])
                    elif m["type"] == "document":
                        await context.bot.send_document(target, m["id"])
            else:
                await context.bot.send_message(target, caption, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to send to {target}: {e}")

    await update.message.reply_text(
        get_text(lang, "thank_you"),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ru")
    context.user_data.clear()
    await update.message.reply_text("❌", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception:", exc_info=context.error)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [CallbackQueryHandler(language_chosen, pattern="^lang_")],
            CONTACT: [
                CallbackQueryHandler(contact_chosen, pattern="^contact_"),
            ],
            REGION: [
                CallbackQueryHandler(region_chosen, pattern="^region_"),
                MessageHandler(filters.CONTACT, phone_received),
            ],
            PROBLEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, problem_text),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, problem_media),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)

    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
