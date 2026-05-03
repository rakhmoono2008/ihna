import os
import logging
import time
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8239199632:AAGF3i4Qsswck4WEhaeLqHNvGBgE1bb2uVw")
ADMIN_ID   = int(os.environ.get("ADMIN_ID", "0"))
ADMIN_ID_2 = int(os.environ.get("ADMIN_ID_2", "0"))
GROUP_ID   = int(os.environ.get("GROUP_ID", "0"))

def is_admin(uid):
    return uid == ADMIN_ID or (ADMIN_ID_2 and uid == ADMIN_ID_2)

LANGUAGE, MENU, CONTACT, REGION, APPEAL, VOL_TYPE, VOL_CONTACT, VOL_REGION = range(8)

blocked_users     = {}
user_languages    = {}
appeals_db        = {}
appeal_counter    = [0]
admin_chat_target = {}   # admin_uid -> user_uid  (active chat)
user_chat_mode    = {}   # user_uid -> True  (user in chat)
chat_waiting      = {}   # user_uid -> True  (waiting for admin to accept)
pending_reply     = {}   # admin_uid -> {appeal_id, user_id}

REGIONS = [
    "Toshkent shahri / г. Ташкент", "Toshkent viloyati / Ташкентская обл.",
    "Samarqand / Самарканд", "Farg'ona / Фергана", "Andijon / Андижан",
    "Namangan / Наманган", "Buxoro / Бухара", "Qashqadaryo / Кашкадарья",
    "Surxondaryo / Сурхандарья", "Xorazm / Хорезм", "Navoiy / Навои",
    "Jizzax / Джизак", "Sirdaryo / Сырдарья", "Qoraqalpogiston / Каракалпакстан",
]

VOL_DIRS = {
    "vol_kids":  {"ru": "🧸 Детские дома и интернаты",   "uz": "🧸 Bolalar uylari va internatlar", "kk": "🧸 Balalar uyleri"},
    "vol_elder": {"ru": "👴 Помощь пожилым людям",        "uz": "👴 Keksalarga yordam",            "kk": "👴 Qarilarğa jardem"},
    "vol_eco":   {"ru": "🌿 Эко-акции и уборка (Хашар)", "uz": "🌿 Eko-aksiyalar (Hashar)",       "kk": "🌿 Eko-aksiyalar"},
    "vol_edu":   {"ru": "🎓 Обучение и тьюторство",       "uz": "🎓 Ta'lim va tyutorlik",          "kk": "🎓 Oqıtıw"},
    "vol_it":    {"ru": "💻 IT-волонтёрство (Pro Bono)",  "uz": "💻 IT-volontyorlik (Pro Bono)",   "kk": "💻 IT-volontyorlik"},
}

TEXTS = {
    "ru": {
        "welcome":        "Добро пожаловать!\n\nЭтот бот предназначен для приёма обращений граждан Узбекистана.\n\nВыберите язык:",
        "menu":           "Главное меню\n\nВыберите действие:",
        "btn_new":        "Новое обращение",
        "btn_my":         "Мои обращения",
        "btn_rules":      "Правила",
        "btn_lang":       "Сменить язык",
        "btn_vol":        "Стать волонтёром",
        "btn_chat":       "Написать нам",
        "choose_vol":     "Выберите направление волонтёрства:",
        "vol_your_choice":"Ваш выбор: {name}",
        "vol_phone_ask":  "Оставьте ваш номер телефона, чтобы мы могли с вами связаться:",
        "vol_phone_btn":  "📱 Поделиться номером",
        "vol_sent":       "Ваша заявка волонтёра отправлена!\n\nМы свяжемся с вами в ближайшее время. Спасибо!",
        "chat_waiting":   "⏳ Ваш запрос отправлен. Ожидайте — администратор скоро подключится.",
        "chat_started_u": "✅ Администратор подключился к чату. Напишите ваш вопрос.\nДля завершения нажмите кнопку ниже.",
        "chat_end_btn":   "🔚 Завершить чат",
        "chat_ended_u":   "Чат завершён. Спасибо за обращение! Возвращаемся в меню.",
        "chat_ended_u_by_admin": "Администратор завершил чат. Возвращаемся в меню.",
        "chat_ended_a":   "✅ Чат с пользователем {name} завершён.",
        "chat_ended_a_by_user": "Пользователь {name} завершил чат.",
        "admin_chat_open":"💬 Чат с {name} открыт.\nВсё что пишете — уходит пользователю напрямую.",
        "admin_chat_end_btn": "🔚 Завершить чат с пользователем",
        "admin_accept_btn": "✅ Принять чат",
        "admin_new_chat": "💬 Новый запрос на чат от {name}:\n\n{text}",
        "choose_contact": "Хотите оставить свой номер телефона?\n\nВнимание: Если останетесь анонимным — мы не сможем связаться с вами.",
        "share_phone":    "📱 Поделиться номером",
        "stay_anon":      "🙈 Остаться анонимным",
        "anon_warning":   "Вы выбрали анонимность.\nОбращение будет передано, но мы не сможем связаться с вами.",
        "choose_region":  "Выберите ваш регион:",
        "vol_region":     "Выберите ваш регион:",
        "send_appeal":    "Опишите ваше обращение\n\nНапишите текст (можно несколько сообщений подряд).\nФото/видео — отправьте по отдельности.\n\nКогда закончите — нажмите кнопку ниже.",
        "submit_btn":     "Отправить обращение",
        "cancel_btn":     "Отмена",
        "thank_you":      "Ваше обращение передано!\n\nСпасибо за доверие. Мы рассмотрим ваше обращение.\n\nВы можете следить за ответами в разделе «Мои обращения».",
        "media_received": "Файл получен. Добавьте ещё или нажмите «Отправить обращение».",
        "text_added":     "Текст добавлен. Продолжайте или нажмите «Отправить обращение».",
        "admin_appeal":   "📨 НОВОЕ ОБРАЩЕНИЕ",
        "admin_vol":      "🤝 НОВЫЙ ВОЛОНТЁР",
        "region_label":   "Регион",
        "contact_label":  "Контакт",
        "anon_label":     "Анонимный",
        "message_label":  "Обращение",
        "vol_dir_label":  "Направление",
        "no_message":     "(только медиафайлы)",
        "no_appeals":     "У вас пока нет обращений.",
        "your_appeals":   "Ваши обращения:",
        "no_replies":     "Ответов пока нет.",
        "reply_label":    "Ответ",
        "reply_received": "📩 Ответ на ваше обращение #{id}:\n\n{reply}",
        "admin_wrote":    "💬 Сообщение от администратора:\n\n{text}",
        "rules":          "ПРАВИЛА ИСПОЛЬЗОВАНИЯ БОТА\n\n1. Запрещено использовать нецензурные и оскорбительные слова.\n2. Запрещено отправлять спам, рекламу, угрозы.\n3. Запрещено отправлять ложные сведения.\n4. Запрещено злоупотреблять ботом.\n\nКАК ПОЛЬЗОВАТЬСЯ:\n- Нажмите «Новое обращение»\n- Выберите контакт или анонимность\n- Выберите регион\n- Опишите ситуацию, прикрепите фото/видео\n- Нажмите «Отправить обращение»\n\nНарушение правил влечёт блокировку.",
        "blocked_perm":   "Вы заблокированы навсегда за нарушение правил.",
        "blocked_temp":   "Вы заблокированы до {until} за нарушение правил.",
        "appeal_id":      "ID обращения",
        "back":           "Назад",
        "phone_prompt":   "Нажмите кнопку ниже чтобы поделиться номером:",
    },
    "uz": {
        "welcome":        "Xush kelibsiz!\n\nBu bot O'zbekiston fuqarolarining murojaatlarini qabul qilish uchun mo'ljallangan.\n\nTilni tanlang:",
        "menu":           "Asosiy menyu\n\nAmalni tanlang:",
        "btn_new":        "Yangi murojaat",
        "btn_my":         "Mening murojaatlarim",
        "btn_rules":      "Qoidalar",
        "btn_lang":       "Tilni o'zgartirish",
        "btn_vol":        "Volontyor bo'lish",
        "btn_chat":       "Bizga yozing",
        "choose_vol":     "Volontyorlik yo'nalishini tanlang:",
        "vol_your_choice":"Tanlovingiz: {name}",
        "vol_phone_ask":  "Biz siz bilan bog'lanishimiz uchun telefon raqamingizni qoldiring:",
        "vol_phone_btn":  "📱 Raqamni ulashish",
        "vol_sent":       "Volontyorlik arizangiz yuborildi!\n\nTez orada siz bilan bog'lanamiz. Rahmat!",
        "chat_waiting":   "⏳ So'rovingiz yuborildi. Kuting — administrator tez orada ulanadi.",
        "chat_started_u": "✅ Administrator chatga ulandi. Savolingizni yozing.\nYakunlash uchun tugmani bosing.",
        "chat_end_btn":   "🔚 Chatni yakunlash",
        "chat_ended_u":   "Chat yakunlandi. Murojaat uchun rahmat! Menyuga qaytamiz.",
        "chat_ended_u_by_admin": "Administrator chatni yakunladi. Menyuga qaytamiz.",
        "chat_ended_a":   "✅ {name} bilan chat yakunlandi.",
        "chat_ended_a_by_user": "Foydalanuvchi {name} chatni yakunladi.",
        "admin_chat_open":"💬 {name} bilan chat ochildi.\nYozgan xabarlaringiz unga boradi.",
        "admin_chat_end_btn": "🔚 Foydalanuvchi bilan chatni yakunlash",
        "admin_accept_btn": "✅ Chatni qabul qilish",
        "admin_new_chat": "💬 {name} dan yangi chat so'rovi:\n\n{text}",
        "choose_contact": "Telefon raqamingizni qoldirmoqchimisiz?\n\nDiqqat: Anonim qolsangiz — biz siz bilan bog'lana olmaymiz.",
        "share_phone":    "📱 Raqamni ulashish",
        "stay_anon":      "🙈 Anonim qolish",
        "anon_warning":   "Siz anonimlikni tanladingiz.\nMurojaat uzatiladi, lekin biz siz bilan bog'lana olmaymiz.",
        "choose_region":  "Viloyatingizni tanlang:",
        "vol_region":     "Viloyatingizni tanlang:",
        "send_appeal":    "Murojaatingizni yozing\n\nMatn yozing (bir nechta xabar yuborishingiz mumkin).\nRasm/video — alohida yuboring.\n\nTayyor bo'lgach — quyidagi tugmani bosing.",
        "submit_btn":     "Murojaatni yuborish",
        "cancel_btn":     "Bekor qilish",
        "thank_you":      "Murojaatingiz qabul qilindi!\n\nKatta rahmat. Murojaatingizni ko'rib chiqamiz.\n\n«Mening murojaatlarim» bo'limida javoblarni kuzatishingiz mumkin.",
        "media_received": "Fayl qabul qilindi. Yana qo'shing yoki «Murojaatni yuborish» ni bosing.",
        "text_added":     "Matn qo'shildi. Davom eting yoki «Murojaatni yuborish» ni bosing.",
        "admin_appeal":   "📨 YANGI MUROJAAT",
        "admin_vol":      "🤝 YANGI VOLONTYOR",
        "region_label":   "Viloyat",
        "contact_label":  "Kontakt",
        "anon_label":     "Anonim",
        "message_label":  "Murojaat",
        "vol_dir_label":  "Yo'nalish",
        "no_message":     "(faqat media fayllar)",
        "no_appeals":     "Sizda hali murojaatlar yo'q.",
        "your_appeals":   "Sizning murojaatlaringiz:",
        "no_replies":     "Hali javob yo'q.",
        "reply_label":    "Javob",
        "reply_received": "📩 #{id}-murojaat javobingiz:\n\n{reply}",
        "admin_wrote":    "💬 Administrator xabari:\n\n{text}",
        "rules":          "BOTDAN FOYDALANISH QOIDALARI\n\n1. Taqiqlangan: so'kinish, haqoratli so'zlar.\n2. Taqiqlangan: spam, reklama, tahdidlar.\n3. Taqiqlangan: yolg'on ma'lumot.\n4. Taqiqlangan: botni suiiste'mol qilish.\n\nQANDAY FOYDALANISH:\n- «Yangi murojaat» tugmasini bosing\n- Raqam qoldiring yoki anonim qoling\n- Viloyatni tanlang\n- Muammoni tasvirlang\n- «Murojaatni yuborish» tugmasini bosing\n\nQoidalarni buzish bloklashga olib keladi.",
        "blocked_perm":   "Siz qoidalarni buzganingiz uchun doimiy ravishda bloklandingiz.",
        "blocked_temp":   "Siz {until} gacha bloklangansiz.",
        "appeal_id":      "Murojaat ID",
        "back":           "Orqaga",
        "phone_prompt":   "Raqamingizni ulashish uchun quyidagi tugmani bosing:",
    },
    "kk": {
        "welcome":        "Xosh keldiñiz!\n\nBul bot O'zbekistan puqaralarının murajaatların qabıl etiw ushın arnalğan.\n\nTildi tanlañ:",
        "menu":           "Bas' menyu\n\nAmaldı tanlañ:",
        "btn_new":        "Jana murajaat",
        "btn_my":         "Menin' murajaatlarım",
        "btn_rules":      "Qaydalar",
        "btn_lang":       "Tildi o'zgertiw",
        "btn_vol":        "Volonter bolıw",
        "btn_chat":       "Bizge jazın",
        "choose_vol":     "Volonterlik bag'darın tanlañ:",
        "vol_your_choice":"Tanlovınız: {name}",
        "vol_phone_ask":  "Biz siz benen baylanısıwımız ushın telefon nomernizdi qaldırın:",
        "vol_phone_btn":  "📱 Nomerni ulasıw",
        "vol_sent":       "Volonterlik arzañız jiberildi!\n\nTez arada siz benen baylanısadı. Rahmet!",
        "chat_waiting":   "⏳ So'rawınız jiberildi. Kütin — administrator tez arada ulanadı.",
        "chat_started_u": "✅ Administrator chatqa ulastı. Sawalınızdı jazın.\nTamawlaw ushın tugmasin basın.",
        "chat_end_btn":   "🔚 Chattı tamawlaw",
        "chat_ended_u":   "Chat tamawlandı. Rahmet! Menyuga qaytamız.",
        "chat_ended_u_by_admin": "Administrator chattı tamawladı. Menyuga qaytamız.",
        "chat_ended_a":   "✅ {name} benen chat tamawlandı.",
        "chat_ended_a_by_user": "Paydalanıwshı {name} chattı tamawladı.",
        "admin_chat_open":"💬 {name} benen chat ashıldı.\nJazg'an xabarlarınız uğan baradi.",
        "admin_chat_end_btn": "🔚 Paydalanıwshı benen chattı tamawlaw",
        "admin_accept_btn": "✅ Chattı qabıl etiw",
        "admin_new_chat": "💬 {name} dan jana chat so'rawı:\n\n{text}",
        "choose_contact": "Telefon nomernizdi qaldırg'ınız keleme?\n\nDıqqat: Anonim qalsañız — biz siz benen baylanısa almaymız.",
        "share_phone":    "📱 Nomerni ulasıw",
        "stay_anon":      "🙈 Anonim qalıw",
        "anon_warning":   "Siz anonimlikti tanladınız.\nMurajaat jetkiziledi, biraq biz siz benen baylanısa almaymız.",
        "choose_region":  "Regionınızdı tanlañ:",
        "vol_region":     "Regionınızdı tanlañ:",
        "send_appeal":    "Murajaatınızdı jazın\n\nMatn jazın (birneshe xabar jibere alasız).\nSuwret/video — bo'leksha jiberin.\n\nTayar bolganda — to'mendegi tugmasin basın.",
        "submit_btn":     "Murajaat jiberiw",
        "cancel_btn":     "Biykar etiw",
        "thank_you":      "Murajaatınız qabıl etildi!\n\nKo'p rahmet. Murajaatınızdı ko'rib shıg'amız.\n\n«Menin' murajaatlarım» bo'liminde jawaplardı ko're alasız.",
        "media_received": "Fayl qabıl etildi. Yana qosın yaki «Murajaat jiberiw» ni basın.",
        "text_added":     "Matn qosıldı. Davom etin yaki «Murajaat jiberiw» ni basın.",
        "admin_appeal":   "📨 JANA MURAJAAT",
        "admin_vol":      "🤝 JANA VOLONTER",
        "region_label":   "Region",
        "contact_label":  "Baylanıs",
        "anon_label":     "Anonim",
        "message_label":  "Murajaat",
        "vol_dir_label":  "Bag'dar",
        "no_message":     "(tek media fayllar)",
        "no_appeals":     "Sizde ha'lirshe murajaatlar joq.",
        "your_appeals":   "Sizin' murajaatlarınız:",
        "no_replies":     "Ha'lirshe jawap joq.",
        "reply_label":    "Jawap",
        "reply_received": "📩 #{id}-murajaat jawabınız:\n\n{reply}",
        "admin_wrote":    "💬 Administrator xabarı:\n\n{text}",
        "rules":          "BOTTAN PAYDALANIW QAYDALARI\n\n1. Tıyım: so'kinish, haqoretli so'zler.\n2. Tıyım: spam, reklama, qorqıtıwlar.\n3. Tıyım: jalg'an mag'lıwmat.\n4. Tıyım: bottı qıyanetlep paydalanıw.\n\nQALAYINSHA PAYDALANIW:\n- «Jana murajaat» tugmasin basın\n- Nomer qaldırın yaki anonim qalın\n- Regionınızdı tanlañ\n- Ma'seleni ta'svirlen\n- «Murajaat jiberiw» tugmasin basın\n\nQaydaların bozıw bloklashg'a alıp keledi.",
        "blocked_perm":   "Siz qaydaların bozg'anınız ushın ma'ngi bloclandınız.",
        "blocked_temp":   "Siz {until} g'a shekem bloclandınız.",
        "appeal_id":      "Murajaat ID",
        "back":           "Artqa",
        "phone_prompt":   "Nomernizdi ulasıw ushın to'mendegi tugmasin basın:",
    },
}


def T(lang, key):
    return TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"].get(key, ""))

def get_lang(uid):
    return user_languages.get(uid, "ru")

def check_block(uid):
    if uid not in blocked_users:
        return False, ""
    until = blocked_users[uid]
    if until == 0:
        return True, "permanent"
    if time.time() < until:
        return True, datetime.fromtimestamp(until).strftime("%d.%m.%Y %H:%M")
    del blocked_users[uid]
    return False, ""

def new_aid():
    appeal_counter[0] += 1
    return appeal_counter[0]

# ─── Keyboards ───────────────────────────────────────────────────

def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇺🇿 O'zbek",  callback_data="lang_uz")],
        [InlineKeyboardButton("🏳️ Qaraqalpaqsha", callback_data="lang_kk")],
    ])

def menu_kb(lang):
    return ReplyKeyboardMarkup([
        [KeyboardButton("✍️ " + T(lang, "btn_new")),  KeyboardButton("📋 " + T(lang, "btn_my"))],
        [KeyboardButton("🤝 " + T(lang, "btn_vol")),  KeyboardButton("📜 " + T(lang, "btn_rules"))],
        [KeyboardButton("💬 " + T(lang, "btn_chat")), KeyboardButton("🌐 " + T(lang, "btn_lang"))],
    ], resize_keyboard=True)

def appeal_contact_kb(lang):
    """For appeals: show phone + anon options"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 " + T(lang, "share_phone"), callback_data="contact_phone")],
        [InlineKeyboardButton("🙈 " + T(lang, "stay_anon"),   callback_data="contact_anon")],
    ])

def vol_phone_kb(lang):
    """For volunteers: only phone button, no anon"""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 " + T(lang, "vol_phone_btn"), request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def region_kb(prefix="reg"):
    rows = []
    for i in range(0, len(REGIONS), 2):
        row = [InlineKeyboardButton(REGIONS[i], callback_data=f"{prefix}_{i}")]
        if i + 1 < len(REGIONS):
            row.append(InlineKeyboardButton(REGIONS[i+1], callback_data=f"{prefix}_{i+1}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def submit_kb(lang):
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ " + T(lang, "submit_btn"))],
        [KeyboardButton("❌ " + T(lang, "cancel_btn"))],
    ], resize_keyboard=True)

def vol_dir_kb(lang):
    rows = []
    for key, names in VOL_DIRS.items():
        rows.append([InlineKeyboardButton(names.get(lang, names["ru"]), callback_data=key)])
    rows.append([InlineKeyboardButton("⬅️ " + T(lang, "back"), callback_data="vol_back")])
    return InlineKeyboardMarkup(rows)

def admin_appeal_kb(aid, uid):
    """Two separate buttons: reply to appeal + open live chat"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Ответить на обращение", callback_data=f"arep_{aid}_{uid}")],
        [InlineKeyboardButton("💬 Открыть прямой чат",    callback_data=f"chat_open_{uid}")],
        [InlineKeyboardButton("⏱ 1 час",    callback_data=f"block_{uid}_1h"),
         InlineKeyboardButton("⏱ 3 часа",   callback_data=f"block_{uid}_3h")],
        [InlineKeyboardButton("📅 1 день",   callback_data=f"block_{uid}_1d"),
         InlineKeyboardButton("📅 1 неделя", callback_data=f"block_{uid}_1w")],
        [InlineKeyboardButton("🚫 Заблокировать навсегда", callback_data=f"block_{uid}_perm")],
    ])

def admin_vol_kb(aid, uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Ответить волонтёру",  callback_data=f"arep_{aid}_{uid}")],
        [InlineKeyboardButton("💬 Открыть прямой чат",  callback_data=f"chat_open_{uid}")],
        [InlineKeyboardButton("⏱ 1 час",    callback_data=f"block_{uid}_1h"),
         InlineKeyboardButton("⏱ 3 часа",   callback_data=f"block_{uid}_3h")],
        [InlineKeyboardButton("📅 1 день",   callback_data=f"block_{uid}_1d"),
         InlineKeyboardButton("📅 1 неделя", callback_data=f"block_{uid}_1w")],
        [InlineKeyboardButton("🚫 Заблокировать навсегда", callback_data=f"block_{uid}_perm")],
    ])

def user_chat_kb(lang):
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔚 " + T(lang, "chat_end_btn"))]],
        resize_keyboard=True
    )

def admin_chat_kb(uid):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔚 Завершить чат с пользователем", callback_data=f"chat_end_{uid}")
    ]])

# ─── Helpers ─────────────────────────────────────────────────────

async def send_to_targets(bot, caption, media_ids, kb):
    targets = [t for t in [ADMIN_ID, ADMIN_ID_2, GROUP_ID] if t]
    send_map = {"photo": bot.send_photo, "video": bot.send_video, "document": bot.send_document}
    for target in targets:
        try:
            if media_ids:
                first = media_ids[0]
                fn = send_map.get(first["type"])
                if fn:
                    await fn(target, first["id"], caption=caption, reply_markup=kb)
                for m in media_ids[1:]:
                    fn2 = send_map.get(m["type"])
                    if fn2:
                        await fn2(target, m["id"])
            else:
                await bot.send_message(target, caption, reply_markup=kb)
        except Exception as e:
            logger.error(f"Send to {target} failed: {e}")

# ─── Handlers ────────────────────────────────────────────────────

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
    lang = {"lang_ru": "ru", "lang_uz": "uz", "lang_kk": "kk"}.get(q.data, "ru")
    ctx.user_data["lang"] = lang
    user_languages[q.from_user.id] = lang
    await q.edit_message_reply_markup(reply_markup=None)
    await q.message.reply_text(T(lang, "menu"), reply_markup=menu_kb(lang))
    return MENU


async def on_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = ctx.user_data.get("lang", get_lang(uid))
    text = update.message.text

    blocked, until = check_block(uid)
    if blocked:
        msg = T(lang, "blocked_perm") if until == "permanent" else T(lang, "blocked_temp").format(until=until)
        await update.message.reply_text(msg)
        return MENU

    # User in chat/waiting mode — handled by user_chat_message handler (group=-1)
    if uid in user_chat_mode or uid in chat_waiting:
        return MENU

    if T(lang, "btn_new") in text:
        await update.message.reply_text(T(lang, "choose_contact"), reply_markup=appeal_contact_kb(lang))
        return CONTACT

    if T(lang, "btn_vol") in text:
        await update.message.reply_text(T(lang, "choose_vol"), reply_markup=vol_dir_kb(lang))
        return VOL_TYPE

    if T(lang, "btn_chat") in text:
        # Put user in waiting mode, not active chat yet
        chat_waiting[uid] = True
        await update.message.reply_text(T(lang, "chat_waiting"), reply_markup=user_chat_kb(lang))
        # Notify all admins with "Accept" button
        user_name = update.effective_user.full_name
        for admin_uid in [a for a in [ADMIN_ID, ADMIN_ID_2] if a]:
            try:
                await ctx.bot.send_message(
                    admin_uid,
                    T("ru", "admin_new_chat").format(name=user_name, text="(нажмите принять)"),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(T("ru", "admin_accept_btn"), callback_data=f"chat_accept_{uid}")
                    ]])
                )
            except Exception as e:
                logger.error(f"Chat notify failed: {e}")
        return MENU

    if T(lang, "btn_my") in text:
        user_appeals = [(k, v) for k, v in appeals_db.items() if v["user_id"] == uid]
        if not user_appeals:
            await update.message.reply_text(T(lang, "no_appeals"))
            return MENU
        await update.message.reply_text(T(lang, "your_appeals"))
        for aid, ap in sorted(user_appeals):
            preview = (ap.get("text") or "")[:80]
            msg = f"#{aid} | {ap['date']}\n{ap['region']}\n{preview or T(lang, 'no_message')}"
            if ap.get("replies"):
                for r in ap["replies"]:
                    msg += f"\n\n{T(lang, 'reply_label')}: {r}"
            else:
                msg += f"\n\n{T(lang, 'no_replies')}"
            await update.message.reply_text(msg)
        return MENU

    if T(lang, "btn_rules") in text:
        await update.message.reply_text(T(lang, "rules"))
        return MENU

    if T(lang, "btn_lang") in text:
        await update.message.reply_text(TEXTS["ru"]["welcome"], reply_markup=lang_kb())
        return LANGUAGE

    return MENU


# ─── VOLUNTEER flow ──────────────────────────────────────────────

async def on_vol_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))

    if q.data == "vol_back":
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(T(lang, "menu"), reply_markup=menu_kb(lang))
        return MENU

    # Get direction name in user's language
    direction = VOL_DIRS.get(q.data, {}).get(lang, VOL_DIRS.get(q.data, {}).get("ru", q.data))
    ctx.user_data["vol_direction"] = direction

    # FIX: show message in correct language
    await q.edit_message_text(T(lang, "vol_your_choice").format(name=direction))
    # FIX: ask phone only (no anon option for volunteers)
    await q.message.reply_text(T(lang, "vol_phone_ask"), reply_markup=vol_phone_kb(lang))
    return VOL_CONTACT


async def on_vol_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Volunteer shared their phone number"""
    lang = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    ctx.user_data["contact"] = update.message.contact.phone_number
    await update.message.reply_text(T(lang, "vol_region"), reply_markup=region_kb("vreg"))
    return VOL_REGION


async def on_vol_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))
    idx  = int(q.data.split("_")[1])
    ctx.user_data["vol_region"] = REGIONS[idx]
    await q.edit_message_text(f"✅ {REGIONS[idx]}")
    return await _submit_volunteer(q.message, ctx, q.from_user)


async def _submit_volunteer(message, ctx, user):
    lang      = ctx.user_data.get("lang", get_lang(user.id))
    direction = ctx.user_data.get("vol_direction", "—")
    region    = ctx.user_data.get("vol_region", "—")
    contact   = ctx.user_data.get("contact", "—")
    aid       = new_aid()
    date_str  = datetime.now().strftime("%d.%m.%Y %H:%M")
    appeals_db[aid] = {
        "user_id": user.id, "region": region, "contact": contact,
        "text": direction, "media": [], "date": date_str,
        "replies": [], "lang": lang, "type": "volunteer",
    }
    contact_str = "+" + contact if contact and contact != "—" else contact
    lang_names  = {"ru": "Русский", "uz": "O'zbek", "kk": "Qaraqalpaqsha"}
    caption = (
        f"{T(lang, 'admin_vol')}\n\n"
        f"Пользователь: {user.full_name} (@{user.username or '—'}) [{user.id}]\n"
        f"ID: #{aid}\n"
        f"{T(lang, 'vol_dir_label')}: {direction}\n"
        f"{T(lang, 'region_label')}: {region}\n"
        f"{T(lang, 'contact_label')}: {contact_str}\n"
        f"Язык: {lang_names.get(lang, lang)}\n"
        f"Дата: {date_str}"
    )
    await send_to_targets(ctx.bot, caption, [], admin_vol_kb(aid, user.id))
    await message.reply_text(T(lang, "vol_sent"), reply_markup=menu_kb(lang))
    ctx.user_data.clear()
    ctx.user_data["lang"] = lang
    return MENU


# ─── APPEAL flow ─────────────────────────────────────────────────

async def on_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))

    if q.data == "contact_phone":
        phone_kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 " + T(lang, "share_phone"), request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await q.edit_message_text(T(lang, "phone_prompt"))
        await q.message.reply_text("👇", reply_markup=phone_kb)
        return REGION
    else:
        ctx.user_data["contact"] = None
        await q.edit_message_text(T(lang, "anon_warning"))
        await q.message.reply_text(T(lang, "choose_region"), reply_markup=region_kb("reg"))
        return REGION


async def on_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    ctx.user_data["contact"] = update.message.contact.phone_number
    await update.message.reply_text(T(lang, "choose_region"), reply_markup=region_kb("reg"))
    return REGION


async def on_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))
    idx  = int(q.data.split("_")[1])
    ctx.user_data["region"]     = REGIONS[idx]
    ctx.user_data["text_parts"] = []
    ctx.user_data["media_ids"]  = []
    await q.edit_message_text(f"✅ {REGIONS[idx]}")
    await q.message.reply_text(T(lang, "send_appeal"), reply_markup=submit_kb(lang))
    return APPEAL


async def on_appeal_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang   = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    text   = update.message.text
    submit = "✅ " + T(lang, "submit_btn")
    cancel = "❌ " + T(lang, "cancel_btn")
    if submit in text:
        return await do_submit(update, ctx)
    if cancel in text:
        ctx.user_data["lang"] = lang
        await update.message.reply_text(T(lang, "menu"), reply_markup=menu_kb(lang))
        return MENU
    ctx.user_data.setdefault("text_parts", []).append(text)
    await update.message.reply_text(T(lang, "text_added"))
    return APPEAL


async def on_appeal_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang      = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    media_ids = ctx.user_data.setdefault("media_ids", [])
    if update.message.photo:
        media_ids.append({"type": "photo", "id": update.message.photo[-1].file_id})
    elif update.message.video:
        media_ids.append({"type": "video", "id": update.message.video.file_id})
    elif update.message.document:
        media_ids.append({"type": "document", "id": update.message.document.file_id})
    if update.message.caption:
        ctx.user_data.setdefault("text_parts", []).append(update.message.caption)
    await update.message.reply_text(T(lang, "media_received"))
    return APPEAL


async def do_submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang       = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    region     = ctx.user_data.get("region", "—")
    contact    = ctx.user_data.get("contact")
    text_parts = ctx.user_data.get("text_parts", [])
    full_text  = "\n\n".join(text_parts) if text_parts else ""
    media_ids  = ctx.user_data.get("media_ids", [])
    user       = update.effective_user
    aid        = new_aid()
    date_str   = datetime.now().strftime("%d.%m.%Y %H:%M")
    appeals_db[aid] = {
        "user_id": user.id, "region": region, "contact": contact,
        "text": full_text, "media": media_ids, "date": date_str,
        "replies": [], "lang": lang, "type": "appeal",
    }
    contact_str = ("+" + contact) if contact else T(lang, "anon_label")
    lang_names  = {"ru": "Русский", "uz": "O'zbek", "kk": "Qaraqalpaqsha"}
    caption = (
        f"{T(lang, 'admin_appeal')}\n\n"
        f"Пользователь: {user.full_name} (@{user.username or '—'}) [{user.id}]\n"
        f"{T(lang, 'appeal_id')}: #{aid}\n"
        f"{T(lang, 'region_label')}: {region}\n"
        f"{T(lang, 'contact_label')}: {contact_str}\n"
        f"Язык: {lang_names.get(lang, lang)}\n"
        f"Дата: {date_str}\n\n"
        f"{T(lang, 'message_label')}:\n"
        f"{full_text if full_text else T(lang, 'no_message')}"
    )
    await send_to_targets(ctx.bot, caption, media_ids, admin_appeal_kb(aid, user.id))
    await update.message.reply_text(T(lang, "thank_you"), reply_markup=menu_kb(lang))
    ctx.user_data.clear()
    ctx.user_data["lang"] = lang
    return MENU


# ─── ADMIN callbacks ─────────────────────────────────────────────

async def on_admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа", show_alert=True)
        return
    await q.answer()
    data = q.data

    # ── Reply to appeal (just text reply, no chat) ──
    if data.startswith("arep_"):
        parts = data.split("_")
        aid   = int(parts[1])
        uid   = int(parts[2])
        pending_reply[q.from_user.id] = {"appeal_id": aid, "user_id": uid}
        await q.message.reply_text(f"✏️ Напишите ответ на обращение #{aid}:")
        return

    # ── Accept chat from waiting user ──
    if data.startswith("chat_accept_"):
        uid = int(data.split("_")[2])
        admin_uid = q.from_user.id
        user_name = (await ctx.bot.get_chat(uid)).full_name
        lang = user_languages.get(uid, "ru")
        # Move from waiting to active
        chat_waiting.pop(uid, None)
        admin_chat_target[admin_uid] = uid
        user_chat_mode[uid] = True
        # Notify user that admin joined
        try:
            await ctx.bot.send_message(uid, T(lang, "chat_started_u"), reply_markup=user_chat_kb(lang))
        except Exception as e:
            logger.error(f"Chat accept notify user failed: {e}")
        # Notify admin
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(
            T("ru", "admin_chat_open").format(name=user_name),
            reply_markup=admin_chat_kb(uid)
        )
        return

    # ── Open live chat directly (from appeal button) ──
    if data.startswith("chat_open_"):
        uid = int(data.split("_")[2])
        admin_uid = q.from_user.id
        user_name = (await ctx.bot.get_chat(uid)).full_name
        lang = user_languages.get(uid, "ru")
        chat_waiting.pop(uid, None)
        admin_chat_target[admin_uid] = uid
        user_chat_mode[uid] = True
        try:
            await ctx.bot.send_message(uid, T(lang, "chat_started_u"), reply_markup=user_chat_kb(lang))
        except Exception as e:
            logger.error(f"Chat open notify failed: {e}")
        await q.message.reply_text(
            T("ru", "admin_chat_open").format(name=user_name),
            reply_markup=admin_chat_kb(uid)
        )
        return

    # ── End chat (admin presses button) ──
    if data.startswith("chat_end_"):
        uid = int(data.split("_")[2])
        admin_uid = q.from_user.id
        user_name = (await ctx.bot.get_chat(uid)).full_name
        lang = user_languages.get(uid, "ru")
        user_chat_mode.pop(uid, None)
        chat_waiting.pop(uid, None)
        admin_chat_target.pop(admin_uid, None)
        try:
            await ctx.bot.send_message(uid, T(lang, "chat_ended_u_by_admin"), reply_markup=menu_kb(lang))
        except Exception: pass
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception: pass
        await q.message.reply_text(T("ru", "chat_ended_a").format(name=user_name))
        return

    # ── Block ──
    if data.startswith("block_"):
        parts = data.split("_")
        uid   = int(parts[1])
        dur   = parts[2]
        durations = {"1h": 3600, "3h": 10800, "1d": 86400, "1w": 604800, "perm": 0}
        labels    = {"1h": "1 час", "3h": "3 часа", "1d": "1 день", "1w": "1 неделю", "perm": "навсегда"}
        secs  = durations.get(dur, 3600)
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
            msg = T(user_lang, "blocked_perm") if secs == 0 else T(user_lang, "blocked_temp").format(until=until_str)
            await ctx.bot.send_message(uid, msg)
        except Exception as e:
            logger.error(f"Block notify failed: {e}")
        await q.message.reply_text(f"✅ Пользователь {uid} заблокирован на {label}.")


async def on_admin_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin typing → goes to active chat user OR as appeal reply"""
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    text = update.message.text or ""

    # Active direct chat takes priority
    admin_uid = uid
    if admin_uid in admin_chat_target:
        target_uid = admin_chat_target[admin_uid]
        user_lang  = user_languages.get(target_uid, "ru")
        try:
            await ctx.bot.send_message(target_uid, T(user_lang, "admin_wrote").format(text=text))
            await update.message.reply_text("✅ Отправлено пользователю.")
        except Exception as e:
            logger.error(f"Admin chat send failed: {e}")
            await update.message.reply_text("❌ Не удалось отправить.")
        # Also save as reply if pending
        if admin_uid in pending_reply:
            info = pending_reply.pop(admin_uid)
            aid  = info["appeal_id"]
            if aid in appeals_db:
                appeals_db[aid]["replies"].append(text)
        return

    # No active chat — check pending reply
    if admin_uid in pending_reply:
        info       = pending_reply.pop(admin_uid)
        aid        = info["appeal_id"]
        target_uid = info["user_id"]
        user_lang  = appeals_db.get(aid, {}).get("lang", user_languages.get(target_uid, "ru"))
        if aid in appeals_db:
            appeals_db[aid]["replies"].append(text)
        try:
            await ctx.bot.send_message(
                target_uid,
                T(user_lang, "reply_received").format(id=aid, reply=text)
            )
            await update.message.reply_text(f"✅ Ответ отправлен пользователю (#{aid}).")
        except Exception as e:
            logger.error(f"Reply send failed: {e}")
            await update.message.reply_text("❌ Не удалось отправить.")


async def user_chat_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Catches messages from users in chat/waiting mode."""
    uid = update.effective_user.id
    if is_admin(uid):
        return
    # Only handle if user is in chat or waiting
    if uid not in user_chat_mode and uid not in chat_waiting:
        return
    lang = get_lang(uid)
    text = update.message.text or ""
    user_name = update.effective_user.full_name
    end_btn = "🔚 " + T(lang, "chat_end_btn")

    # User ends chat
    if end_btn in text:
        was_active = uid in user_chat_mode
        user_chat_mode.pop(uid, None)
        chat_waiting.pop(uid, None)
        # Find admin with this chat
        admin_uid_key = next((k for k, v in admin_chat_target.items() if v == uid), None)
        if admin_uid_key:
            admin_chat_target.pop(admin_uid_key, None)
            try:
                await ctx.bot.send_message(
                    admin_uid_key,
                    T("ru", "chat_ended_a_by_user").format(name=user_name)
                )
            except Exception: pass
        else:
            # Notify all admins if no one accepted
            for a in [a for a in [ADMIN_ID, ADMIN_ID_2] if a]:
                try:
                    await ctx.bot.send_message(a, f"Пользователь {user_name} отменил запрос на чат.")
                except Exception: pass
        await update.message.reply_text(T(lang, "chat_ended_u"), reply_markup=menu_kb(lang))
    
    # If user is only waiting (no admin accepted yet) — forward as new message
    if uid in chat_waiting:
        for a in [a for a in [ADMIN_ID, ADMIN_ID_2] if a]:
            try:
                await ctx.bot.send_message(
                    a,
                    T("ru", "admin_new_chat").format(name=user_name, text=text),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(T("ru", "admin_accept_btn"), callback_data=f"chat_accept_{uid}")
                    ]])
                )
            except Exception as e:
                logger.error(f"Waiting chat forward failed: {e}")
        return

    # User is in active chat — forward to the admin who accepted
    for admin_uid, target_uid in list(admin_chat_target.items()):
        if target_uid == uid:
            try:
                await ctx.bot.send_message(
                    admin_uid,
                    f"💬 {user_name}:\n{text}",
                    reply_markup=admin_chat_kb(uid)
                )
            except Exception as e:
                logger.error(f"Chat forward failed: {e}")
            return
    # No admin has active session — broadcast
    for a in [a for a in [ADMIN_ID, ADMIN_ID_2] if a]:
        try:
            await ctx.bot.send_message(
                a,
                f"💬 {user_name}:\n{text}",
                reply_markup=admin_chat_kb(uid)
            )
        except Exception as e:
            logger.error(f"Chat broadcast failed: {e}")


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Error:", exc_info=ctx.error)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE:    [CallbackQueryHandler(on_language, pattern="^lang_")],
            MENU:        [MessageHandler(filters.TEXT & ~filters.COMMAND, on_menu)],
            CONTACT:     [CallbackQueryHandler(on_contact, pattern="^contact_")],
            REGION:      [
                CallbackQueryHandler(on_region, pattern="^reg_"),
                MessageHandler(filters.CONTACT, on_phone),
            ],
            APPEAL:      [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_appeal_text),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, on_appeal_media),
            ],
            VOL_TYPE:    [CallbackQueryHandler(on_vol_type,
                           pattern="^(vol_kids|vol_elder|vol_eco|vol_edu|vol_it|vol_back)$")],
            VOL_CONTACT: [MessageHandler(filters.CONTACT, on_vol_phone)],
            VOL_REGION:  [CallbackQueryHandler(on_vol_region, pattern="^vreg_")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(
        on_admin_callback,
        pattern="^(arep_|chat_accept_|chat_open_|chat_end_|block_)"
    ))

    # group=1: runs AFTER conversation (conv handles /start, menu etc)
    # Admin messages handler
    admin_filter = filters.User(ADMIN_ID)
    if ADMIN_ID_2:
        admin_filter = admin_filter | filters.User(ADMIN_ID_2)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & admin_filter,
        on_admin_message
    ), group=1)

    # group=1: user chat handler (also after conv, but conv returns MENU for chat users)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        user_chat_message
    ), group=1)

    app.add_error_handler(on_error)

    logger.info("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
