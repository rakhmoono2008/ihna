import os
import logging
import time
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8239199632:AAGF3i4Qsswck4WEhaeLqHNvGBgE1bb2uVw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

# States
LANGUAGE, MENU, CONTACT, REGION, APPEAL = range(5)

# Storage
blocked_users = {}   # {user_id: timestamp or 0=permanent}
user_languages = {}  # {user_id: lang}
appeals_db = {}      # {appeal_id: {...}}
appeal_counter = [0]
pending_reply = {}   # {admin_id: {appeal_id, user_id}}

# ───────────────────────────────────────────────────────────────
# TEXTS
# ───────────────────────────────────────────────────────────────
TEXTS = {
    "ru": {
        "welcome": "Добро пожаловать!\n\nЭтот бот предназначен для приёма обращений граждан Узбекистана.\n\nВыберите язык:",
        "menu": "Главное меню\n\nВыберите действие:",
        "btn_new": "Новое обращение",
        "btn_my": "Мои обращения",
        "btn_rules": "Правила",
        "btn_lang": "Сменить язык",
        "choose_contact": "Контактные данные\n\nХотите оставить свой номер телефона?\n\nВнимание: Если вы останетесь анонимным — мы не сможем связаться с вами для уточнения деталей.",
        "share_phone": "Поделиться номером",
        "stay_anon": "Остаться анонимным",
        "anon_warning": "Вы выбрали анонимность.\nОбращение будет передано, но мы не сможем связаться с вами.",
        "choose_region": "Выберите ваш регион:",
        "send_appeal": "Опишите ваше обращение\n\nНапишите текст.\nЕсли есть фото или видео — отправьте их по отдельности, бот соберёт всё вместе.\n\nКогда закончите — нажмите кнопку Отправить обращение.",
        "submit_btn": "Отправить обращение",
        "cancel_btn": "Отмена",
        "thank_you": "Ваше обращение передано!\n\nСпасибо большое за доверие. Мы обязательно рассмотрим ваше обращение.\n\nВы можете следить за ответами в разделе Мои обращения.",
        "media_received": "Файл получен. Добавьте ещё или нажмите Отправить обращение.",
        "admin_header": "НОВОЕ ОБРАЩЕНИЕ",
        "region_label": "Регион",
        "contact_label": "Контакт",
        "anon_label": "Анонимный",
        "message_label": "Обращение",
        "no_message": "(только медиафайлы)",
        "no_appeals": "У вас пока нет обращений.",
        "your_appeals": "Ваши обращения:",
        "no_replies": "Ответов пока нет.",
        "reply_label": "Ответ",
        "reply_from_admin": "Ответ на ваше обращение #{id}:\n\n{reply}",
        "rules": (
            "ПРАВИЛА ИСПОЛЬЗОВАНИЯ БОТА\n\n"
            "1. Запрещено использовать нецензурные и оскорбительные слова.\n"
            "2. Запрещено отправлять спам, рекламу, угрозы.\n"
            "3. Запрещено отправлять ложные или заведомо недостоверные сведения.\n"
            "4. Запрещено злоупотреблять ботом.\n\n"
            "КАК ПОЛЬЗОВАТЬСЯ:\n"
            "- Нажмите Новое обращение\n"
            "- Выберите — оставить номер или остаться анонимным\n"
            "- Выберите регион\n"
            "- Опишите проблему, можно прикрепить фото/видео\n"
            "- Нажмите Отправить обращение\n\n"
            "Нарушение правил влечёт блокировку на определённый срок."
        ),
        "blocked_perm": "Вы заблокированы навсегда за нарушение правил.",
        "blocked_temp": "Вы заблокированы до {until} за нарушение правил.",
        "share_phone_btn": "Отправить номер",
        "appeal_id": "ID обращения",
        "date": "Дата",
        "lang_name": "Русский",
    },
    "uz": {
        "welcome": "Xush kelibsiz!\n\nBu bot O'zbekiston fuqarolarining murojaatlarini qabul qilish uchun mo'ljallangan.\n\nTilni tanlang:",
        "menu": "Asosiy menyu\n\nAmalni tanlang:",
        "btn_new": "Yangi murojaat",
        "btn_my": "Mening murojaatlarim",
        "btn_rules": "Qoidalar",
        "btn_lang": "Tilni o'zgartirish",
        "choose_contact": "Aloqa ma'lumotlari\n\nTelefon raqamingizni qoldirmoqchimisiz?\n\nDiqqat: Anonim qolsangiz — biz siz bilan bog'lana olmaymiz.",
        "share_phone": "Raqamni ulashish",
        "stay_anon": "Anonim qolish",
        "anon_warning": "Siz anonimlikni tanladingiz.\nMurojaat uzatiladi, lekin biz siz bilan bog'lana olmaymiz.",
        "choose_region": "Viloyatingizni tanlang:",
        "send_appeal": "Murojaatingizni yozing\n\nMatn yozing.\nRasm yoki video bo'lsa — alohida yuboring, bot hammasini yig'adi.\n\nTayyor bo'lgach — Murojaatni yuborish tugmasini bosing.",
        "submit_btn": "Murojaatni yuborish",
        "cancel_btn": "Bekor qilish",
        "thank_you": "Murojaatingiz qabul qilindi!\n\nKatta rahmat. Murojaatingizni ko'rib chiqamiz.\n\nMening murojaatlarim bo'limida javoblarni kuzatishingiz mumkin.",
        "media_received": "Fayl qabul qilindi. Yana qo'shing yoki Murojaatni yuborish tugmasini bosing.",
        "admin_header": "YANGI MUROJAAT",
        "region_label": "Viloyat",
        "contact_label": "Kontakt",
        "anon_label": "Anonim",
        "message_label": "Murojaat",
        "no_message": "(faqat media fayllar)",
        "no_appeals": "Sizda hali murojaatlar yo'q.",
        "your_appeals": "Sizning murojaatlaringiz:",
        "no_replies": "Hali javob yo'q.",
        "reply_label": "Javob",
        "reply_from_admin": "#{id}-murojaat javobingiz:\n\n{reply}",
        "rules": (
            "BOTDAN FOYDALANISH QOIDALARI\n\n"
            "1. Taqiqlangan: so'kinish, haqoratli so'zlar.\n"
            "2. Taqiqlangan: spam, reklama, tahdidlar.\n"
            "3. Taqiqlangan: yolg'on yoki noto'g'ri ma'lumot.\n"
            "4. Taqiqlangan: botni suiiste'mol qilish.\n\n"
            "QANDAY FOYDALANISH:\n"
            "- Yangi murojaat tugmasini bosing\n"
            "- Raqam qoldirish yoki anonim qolishni tanlang\n"
            "- Viloyatni tanlang\n"
            "- Muammoni tasvirlang, rasm/video ilova qiling\n"
            "- Murojaatni yuborish tugmasini bosing\n\n"
            "Qoidalarni buzish bloklashga olib keladi."
        ),
        "blocked_perm": "Siz qoidalarni buzganingiz uchun doimiy ravishda bloklandingiz.",
        "blocked_temp": "Siz {until} gacha bloklangansiz.",
        "share_phone_btn": "Raqam yuborish",
        "appeal_id": "Murojaat ID",
        "date": "Sana",
        "lang_name": "O'zbek",
    },
    "kk": {
        "welcome": "Xosh keldiñiz!\n\nBul bot O'zbekistan puqaralarinin murajaatların qabıl etiw ushın arnalgan.\n\nTildi tanlañ:",
        "menu": "Bas menyu\n\nAmaldı tanlañ:",
        "btn_new": "Jana murajaat",
        "btn_my": "Menin murajaatlarım",
        "btn_rules": "Qaydalar",
        "btn_lang": "Tildi ozgertiw",
        "choose_contact": "Baylanıs maglıwmatları\n\nTelefon nomerindi qaldırgınız keleme?\n\nDıqqat: Anonim qalsañız — biz siz benen baylanısa almaymız.",
        "share_phone": "Nomerni ulasıw",
        "stay_anon": "Anonim qalıw",
        "anon_warning": "Siz anonimlikti tanladınız.\nMurajaat jetkiziledi, biraq biz siz benen baylanısa almaymız.",
        "choose_region": "Regionınızdı tanlañ:",
        "send_appeal": "Murajaatınızdı jazın\n\nMatn jazın.\nSuwret ya'ki video bolsa — boleksha jiberin, bot barlıgın yıgnap alır.\n\nTayar bolganda — Murajaat jiberiw tugmasin basın.",
        "submit_btn": "Murajaat jiberiw",
        "cancel_btn": "Biykar etiw",
        "thank_you": "Murajaatınız qabıl etildi!\n\nKop rahmet. Murajaatınızdı korib shıgamız.\n\nMenin murajaatlarım boliminde jawaplardı kore alasız.",
        "media_received": "Fayl qabıl etildi. Yana qosın ya'ki Murajaat jiberiw tugmasin basın.",
        "admin_header": "JANA MURAJAAT",
        "region_label": "Region",
        "contact_label": "Baylanıs",
        "anon_label": "Anonim",
        "message_label": "Murajaat",
        "no_message": "(tek media fayllar)",
        "no_appeals": "Sizde halirshe murajaatlar joq.",
        "your_appeals": "Sizin murajaatlarınız:",
        "no_replies": "Halirshe jawap joq.",
        "reply_label": "Jawap",
        "reply_from_admin": "#{id}-murajaat jawabınız:\n\n{reply}",
        "rules": (
            "BOTTAN PAYDALANIW QAYDALARI\n\n"
            "1. Tıyım salıngan: sokinish, haqoretli sozler.\n"
            "2. Tıyım salıngan: spam, reklama, qorqıtıwlar.\n"
            "3. Tıyım salıngan: jalgan maglıwmat.\n"
            "4. Tıyım salıngan: bottı qıyanetlep paydalanıw.\n\n"
            "QALAYINSHA PAYDALANIW KEREK:\n"
            "- Jana murajaat tugmasin basın\n"
            "- Nomer qaldırıw ya'ki anonim qalıwdı tanlañ\n"
            "- Regionınızdı tanlañ\n"
            "- Maseleni suwriting\n"
            "- Murajaat jiberiw tugmasin basın\n\n"
            "Qaydaların bozıw bloklashga alıp keledi."
        ),
        "blocked_perm": "Siz qaydaların bozganınız ushın mangi bloclandınız.",
        "blocked_temp": "Siz {until} ga shekem bloclandınız.",
        "share_phone_btn": "Nomerni jiberiw",
        "appeal_id": "Murajaat ID",
        "date": "Sana",
        "lang_name": "Qaraqalpaqsha",
    }
}

REGIONS = [
    "Toshkent shahri / г. Ташкент",
    "Toshkent viloyati / Ташкентская обл.",
    "Samarqand / Самарканд",
    "Farg'ona / Фергана",
    "Andijon / Андижан",
    "Namangan / Наманган",
    "Buxoro / Бухара",
    "Qashqadaryo / Кашкадарья",
    "Surxondaryo / Сурхандарья",
    "Xorazm / Хорезм",
    "Navoiy / Навои",
    "Jizzax / Джизак",
    "Sirdaryo / Сырдарья",
    "Qoraqalpogiston / Каракалпакстан",
]

# ───────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────

def T(lang, key):
    return TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"].get(key, ""))

def get_lang(user_id):
    return user_languages.get(user_id, "ru")

def check_block(user_id):
    if user_id not in blocked_users:
        return False, ""
    until = blocked_users[user_id]
    if until == 0:
        return True, "permanent"
    if time.time() < until:
        return True, datetime.fromtimestamp(until).strftime("%d.%m.%Y %H:%M")
    del blocked_users[user_id]
    return False, ""

def new_appeal_id():
    appeal_counter[0] += 1
    return appeal_counter[0]

# ───────────────────────────────────────────────────────────────
# KEYBOARDS
# ───────────────────────────────────────────────────────────────

def lang_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        ],
        [InlineKeyboardButton("🏳️ Qaraqalpaqsha", callback_data="lang_kk")],
    ])

def menu_kb(lang):
    return ReplyKeyboardMarkup([
        [KeyboardButton("✍️ " + T(lang, "btn_new")), KeyboardButton("📋 " + T(lang, "btn_my"))],
        [KeyboardButton("📜 " + T(lang, "btn_rules")), KeyboardButton("🌐 " + T(lang, "btn_lang"))],
    ], resize_keyboard=True)

def contact_kb(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 " + T(lang, "share_phone"), callback_data="contact_phone")],
        [InlineKeyboardButton("🙈 " + T(lang, "stay_anon"), callback_data="contact_anon")],
    ])

def region_kb():
    rows = []
    for i in range(0, len(REGIONS), 2):
        row = [InlineKeyboardButton(REGIONS[i], callback_data=f"reg_{i}")]
        if i + 1 < len(REGIONS):
            row.append(InlineKeyboardButton(REGIONS[i+1], callback_data=f"reg_{i+1}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def submit_kb(lang):
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ " + T(lang, "submit_btn"))],
        [KeyboardButton("❌ " + T(lang, "cancel_btn"))],
    ], resize_keyboard=True)

def admin_kb(appeal_id, user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить пользователю", callback_data=f"reply_{appeal_id}_{user_id}")],
        [
            InlineKeyboardButton("⏱ 1 час", callback_data=f"block_{user_id}_1h"),
            InlineKeyboardButton("⏱ 3 часа", callback_data=f"block_{user_id}_3h"),
        ],
        [
            InlineKeyboardButton("📅 1 день", callback_data=f"block_{user_id}_1d"),
            InlineKeyboardButton("📅 1 неделя", callback_data=f"block_{user_id}_1w"),
        ],
        [InlineKeyboardButton("🚫 Заблокировать навсегда", callback_data=f"block_{user_id}_perm")],
    ])

# ───────────────────────────────────────────────────────────────
# HANDLERS
# ───────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    blocked, until = check_block(uid)
    if blocked:
        lang = get_lang(uid)
        msg = T(lang, "blocked_perm") if until == "permanent" else T(lang, "blocked_temp").format(until=until)
        await update.message.reply_text(msg)
        return ConversationHandler.END

    ctx.user_data.clear()
    await update.message.reply_text(TEXTS["ru"]["welcome"], reply_markup=lang_kb())
    return LANGUAGE


async def on_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = {"lang_ru": "ru", "lang_uz": "uz", "lang_kk": "kk"}.get(q.data, "ru")
    ctx.user_data["lang"] = lang
    user_languages[uid] = lang
    await q.message.reply_text(T(lang, "menu"), reply_markup=menu_kb(lang))
    return MENU


async def on_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = ctx.user_data.get("lang", get_lang(uid))
    text = update.message.text

    blocked, until = check_block(uid)
    if blocked:
        msg = T(lang, "blocked_perm") if until == "permanent" else T(lang, "blocked_temp").format(until=until)
        await update.message.reply_text(msg)
        return MENU

    # Strip emoji prefix for comparison
    clean = text.lstrip("✍️📋📜🌐 ").strip()

    if clean == T(lang, "btn_new"):
        await update.message.reply_text(T(lang, "choose_contact"), reply_markup=contact_kb(lang))
        return CONTACT

    if clean == T(lang, "btn_my"):
        user_appeals = [(k, v) for k, v in appeals_db.items() if v["user_id"] == uid]
        if not user_appeals:
            await update.message.reply_text(T(lang, "no_appeals"))
            return MENU
        await update.message.reply_text(T(lang, "your_appeals"))
        for aid, ap in sorted(user_appeals):
            preview = (ap.get("text") or "")[:80]
            msg = (
                f"#{aid} | {ap['date']}\n"
                f"{ap['region']}\n"
                f"{preview or T(lang, 'no_message')}"
            )
            if ap.get("replies"):
                for r in ap["replies"]:
                    msg += f"\n\n{T(lang, 'reply_label')}: {r}"
            else:
                msg += f"\n\n{T(lang, 'no_replies')}"
            await update.message.reply_text(msg)
        return MENU

    if clean == T(lang, "btn_rules"):
        await update.message.reply_text(T(lang, "rules"))
        return MENU

    if clean == T(lang, "btn_lang"):
        await update.message.reply_text(TEXTS["ru"]["welcome"], reply_markup=lang_kb())
        return LANGUAGE

    return MENU


async def on_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))

    if q.data == "contact_phone":
        btn_labels = {"ru": "Отправить номер", "uz": "Raqam yuborish", "kk": "Nomerni jiberiw"}
        btn = btn_labels.get(lang, "Отправить номер")
        phone_kb = ReplyKeyboardMarkup(
            [[KeyboardButton(btn, request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        prompts = {
            "ru": "Нажмите кнопку ниже, чтобы поделиться номером:",
            "uz": "Raqamni ulashish uchun quyidagi tugmani bosing:",
            "kk": "Nomerni ulasıw ushın to'mendegi tugmasin basın:"
        }
        await q.edit_message_text(prompts.get(lang, ""))
        await q.message.reply_text("👇", reply_markup=phone_kb)
        return REGION
    else:
        ctx.user_data["contact"] = None
        await q.edit_message_text(T(lang, "anon_warning"))
        await q.message.reply_text(T(lang, "choose_region"), reply_markup=region_kb())
        return REGION


async def on_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    ctx.user_data["contact"] = update.message.contact.phone_number
    await update.message.reply_text(T(lang, "choose_region"), reply_markup=region_kb())
    return REGION


async def on_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))
    idx = int(q.data.split("_")[1])
    ctx.user_data["region"] = REGIONS[idx]
    ctx.user_data["media_ids"] = []
    ctx.user_data["text_message"] = ""
    await q.edit_message_text(f"✅ {REGIONS[idx]}")
    await q.message.reply_text(T(lang, "send_appeal"), reply_markup=submit_kb(lang))
    return APPEAL


async def on_appeal_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    text = update.message.text
    submit = "✅ " + T(lang, "submit_btn")
    cancel = "❌ " + T(lang, "cancel_btn")
    if text == submit:
        return await do_submit(update, ctx)
    if text == cancel:
        ctx.user_data["lang"] = lang
        await update.message.reply_text(T(lang, "menu"), reply_markup=menu_kb(lang))
        return MENU
    ctx.user_data["text_message"] = text
    return APPEAL


async def on_appeal_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    media_ids = ctx.user_data.setdefault("media_ids", [])
    if update.message.photo:
        media_ids.append({"type": "photo", "id": update.message.photo[-1].file_id})
    elif update.message.video:
        media_ids.append({"type": "video", "id": update.message.video.file_id})
    elif update.message.document:
        media_ids.append({"type": "document", "id": update.message.document.file_id})
    if update.message.caption:
        ctx.user_data["text_message"] = update.message.caption
    await update.message.reply_text(T(lang, "media_received"))
    return APPEAL


async def do_submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    region = ctx.user_data.get("region", "—")
    contact = ctx.user_data.get("contact")
    text_msg = ctx.user_data.get("text_message", "")
    media_ids = ctx.user_data.get("media_ids", [])
    user = update.effective_user

    aid = new_appeal_id()
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    appeals_db[aid] = {
        "user_id": user.id, "region": region, "contact": contact,
        "text": text_msg, "media": media_ids, "date": date_str,
        "replies": [], "lang": lang,
    }

    contact_str = ("+" + contact) if contact else T(lang, "anon_label")
    lang_names = {"ru": "Русский", "uz": "O'zbek", "kk": "Qaraqalpaqsha"}

    caption = (
        f"{T(lang, 'admin_header')}\n\n"
        f"Пользователь: {user.full_name} (@{user.username or '—'}) [{user.id}]\n"
        f"{T(lang, 'appeal_id')}: #{aid}\n"
        f"{T(lang, 'region_label')}: {region}\n"
        f"{T(lang, 'contact_label')}: {contact_str}\n"
        f"Язык: {lang_names.get(lang, lang)}\n"
        f"Дата: {date_str}\n\n"
        f"{T(lang, 'message_label')}:\n"
        f"{text_msg if text_msg else T(lang, 'no_message')}"
    )

    kb = admin_kb(aid, user.id)
    targets = [t for t in [ADMIN_ID, GROUP_ID] if t]

    for target in targets:
        try:
            if media_ids:
                first = media_ids[0]
                send_funcs = {
                    "photo": ctx.bot.send_photo,
                    "video": ctx.bot.send_video,
                    "document": ctx.bot.send_document,
                }
                fn = send_funcs.get(first["type"])
                if fn:
                    await fn(target, first["id"], caption=caption, reply_markup=kb)
                for m in media_ids[1:]:
                    fn2 = send_funcs.get(m["type"])
                    if fn2:
                        await fn2(target, m["id"])
            else:
                await ctx.bot.send_message(target, caption, reply_markup=kb)
        except Exception as e:
            logger.error(f"Send to {target} failed: {e}")

    await update.message.reply_text(T(lang, "thank_you"), reply_markup=menu_kb(lang))
    ctx.user_data.clear()
    ctx.user_data["lang"] = lang
    return MENU


# ───────────────────────────────────────────────────────────────
# ADMIN CALLBACKS (outside conversation)
# ───────────────────────────────────────────────────────────────

async def on_admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Нет доступа", show_alert=True)
        return
    await q.answer()
    data = q.data

    if data.startswith("reply_"):
        _, aid, uid = data.split("_")
        pending_reply[ADMIN_ID] = {"appeal_id": int(aid), "user_id": int(uid)}
        await q.message.reply_text(f"Напишите ответ для обращения #{aid}:")
        return

    if data.startswith("block_"):
        parts = data.split("_")
        uid = int(parts[1])
        dur = parts[2]
        durations = {"1h": 3600, "3h": 10800, "1d": 86400, "1w": 604800, "perm": 0}
        labels = {"1h": "1 час", "3h": "3 часа", "1d": "1 день", "1w": "1 неделю", "perm": "навсегда"}
        secs = durations.get(dur, 3600)
        label = labels.get(dur, dur)

        if secs == 0:
            blocked_users[uid] = 0
            until_str = "навсегда"
        else:
            until_ts = time.time() + secs
            blocked_users[uid] = until_ts
            until_str = datetime.fromtimestamp(until_ts).strftime("%d.%m.%Y %H:%M")

        user_lang = user_languages.get(uid, "ru")
        try:
            if secs == 0:
                await ctx.bot.send_message(uid, T(user_lang, "blocked_perm"))
            else:
                await ctx.bot.send_message(uid, T(user_lang, "blocked_temp").format(until=until_str))
        except Exception as e:
            logger.error(f"Block notify failed: {e}")

        await q.message.reply_text(f"Пользователь {uid} заблокирован на {label}.")


async def on_admin_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID or uid not in pending_reply:
        return

    info = pending_reply.pop(uid)
    aid = info["appeal_id"]
    target_uid = info["user_id"]
    reply_text = update.message.text

    if aid in appeals_db:
        appeals_db[aid]["replies"].append(reply_text)
        user_lang = appeals_db[aid].get("lang", "ru")
    else:
        user_lang = user_languages.get(target_uid, "ru")

    try:
        await ctx.bot.send_message(
            target_uid,
            T(user_lang, "reply_from_admin").format(id=aid, reply=reply_text)
        )
        await update.message.reply_text(f"Ответ отправлен пользователю (обращение #{aid}).")
    except Exception as e:
        logger.error(f"Reply send failed: {e}")
        await update.message.reply_text("Не удалось отправить ответ.")


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Error:", exc_info=ctx.error)


# ───────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [CallbackQueryHandler(on_language, pattern="^lang_")],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_menu)],
            CONTACT: [CallbackQueryHandler(on_contact, pattern="^contact_")],
            REGION: [
                CallbackQueryHandler(on_region, pattern="^reg_"),
                MessageHandler(filters.CONTACT, on_phone),
            ],
            APPEAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_appeal_text),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, on_appeal_media),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(on_admin_callback, pattern="^(reply_|block_)"))
    if ADMIN_ID:
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
            on_admin_reply
        ))
    app.add_error_handler(on_error)

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
