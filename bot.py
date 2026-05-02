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
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "0"))
GROUP_ID  = int(os.environ.get("GROUP_ID", "0"))

LANGUAGE, MENU, CONTACT, REGION, APPEAL, VOL_TYPE, VOL_REGION = range(7)

blocked_users     = {}
user_languages    = {}
appeals_db        = {}
appeal_counter    = [0]
admin_chat_target = {}
user_chat_mode    = {}
pending_reply     = {}

VOL_DIRS = {
    "vol_kids":  {"ru": "Detskie doma i internaty",  "uz": "Bolalar uylari",       "kk": "Balalar uyleri"},
    "vol_elder": {"ru": "Pomoshch pozhilym lyudyam", "uz": "Keksalarga yordam",    "kk": "Qarilar jardem"},
    "vol_eco":   {"ru": "Eko-akcii i uborka Hashar", "uz": "Eko-aksiyalar Hashar", "kk": "Eko-aksiyalar"},
    "vol_edu":   {"ru": "Obuchenie i tyutorstvo",    "uz": "Ta'lim va tyutorlik",  "kk": "Oqıtıw"},
    "vol_it":    {"ru": "IT-volontyorstvo Pro Bono", "uz": "IT-volontyorlik",      "kk": "IT-volontyorlik"},
}

VOL_EMOJIS = {
    "vol_kids": "🧸", "vol_elder": "👴", "vol_eco": "🌿", "vol_edu": "🎓", "vol_it": "💻"
}

REGIONS = [
    "Toshkent shahri / г. Ташкент", "Toshkent viloyati / Ташкентская обл.",
    "Samarqand / Самарканд", "Farg'ona / Фергана", "Andijon / Андижан",
    "Namangan / Наманган", "Buxoro / Бухара", "Qashqadaryo / Кашкадарья",
    "Surxondaryo / Сурхандарья", "Xorazm / Хорезм", "Navoiy / Навои",
    "Jizzax / Джизак", "Sirdaryo / Сырдарья", "Qoraqalpogiston / Каракалпакстан",
]

TEXTS = {
    "ru": {
        "welcome": "Добро пожаловать!\n\nЭтот бот предназначен для приёма обращений граждан Узбекистана.\n\nВыберите язык:",
        "menu": "Главное меню\n\nВыберите действие:",
        "btn_new": "Новое обращение",
        "btn_my": "Мои обращения",
        "btn_rules": "Правила",
        "btn_lang": "Сменить язык",
        "btn_vol": "Стать волонтёром",
        "choose_vol": "Выберите направление волонтёрства:",
        "vol_contact": "Оставьте номер телефона чтобы мы могли с вами связаться:",
        "vol_sent": "Ваша заявка волонтёра отправлена!\n\nМы свяжемся с вами в ближайшее время. Спасибо!",
        "btn_chat": "Написать нам",
        "chat_started": "Вы начали прямой чат с нами. Напишите ваш вопрос:",
        "chat_end_btn": "Завершить чат",
        "chat_ended_u": "Чат завершён. Возвращаемся в меню.",
        "chat_ended_a": "Чат с пользователем завершён.",
        "choose_contact": "Хотите оставить свой номер телефона?\n\nВнимание: Если останетесь анонимным — мы не сможем связаться с вами.",
        "share_phone": "Поделиться номером",
        "stay_anon": "Остаться анонимным",
        "anon_warning": "Вы выбрали анонимность.\nОбращение будет передано, но мы не сможем связаться с вами.",
        "choose_region": "Выберите ваш регион:",
        "vol_region": "Выберите ваш регион:",
        "send_appeal": "Опишите ваше обращение\n\nНапишите текст (можно несколько сообщений подряд).\nФото/видео — отправьте по отдельности.\n\nКогда закончите — нажмите кнопку Отправить обращение.",
        "submit_btn": "Отправить обращение",
        "cancel_btn": "Отмена",
        "thank_you": "Ваше обращение передано!\n\nСпасибо за доверие. Мы рассмотрим ваше обращение.\n\nВы можете следить за ответами в разделе Мои обращения.",
        "media_received": "Файл получен. Продолжайте добавлять или нажмите Отправить обращение.",
        "text_added": "Текст добавлен. Продолжайте или нажмите Отправить обращение.",
        "admin_appeal": "НОВОЕ ОБРАЩЕНИЕ",
        "admin_vol": "НОВЫЙ ВОЛОНТЁР",
        "region_label": "Регион",
        "contact_label": "Контакт",
        "anon_label": "Анонимный",
        "message_label": "Обращение",
        "vol_dir_label": "Направление",
        "no_message": "только медиафайлы",
        "no_appeals": "У вас пока нет обращений.",
        "your_appeals": "Ваши обращения:",
        "no_replies": "Ответов пока нет.",
        "reply_label": "Ответ",
        "reply_received": "Ответ на ваше обращение #{id}:\n\n{reply}",
        "rules": "ПРАВИЛА ИСПОЛЬЗОВАНИЯ БОТА\n\n1. Запрещено использовать нецензурные и оскорбительные слова.\n2. Запрещено отправлять спам, рекламу, угрозы.\n3. Запрещено отправлять ложные сведения.\n4. Запрещено злоупотреблять ботом.\n\nКАК ПОЛЬЗОВАТЬСЯ:\n- Нажмите Новое обращение\n- Выберите контакт или анонимность\n- Выберите регион\n- Опишите ситуацию, прикрепите фото/видео\n- Нажмите Отправить обращение\n\nНарушение правил влечёт блокировку.",
        "blocked_perm": "Вы заблокированы навсегда за нарушение правил.",
        "blocked_temp": "Вы заблокированы до {until} за нарушение правил.",
        "appeal_id": "ID обращения",
        "back": "Назад",
        "admin_wrote": "Ответ: {text}",
    },
    "uz": {
        "welcome": "Xush kelibsiz!\n\nBu bot O'zbekiston fuqarolarining murojaatlarini qabul qilish uchun.\n\nTilni tanlang:",
        "menu": "Asosiy menyu\n\nAmalni tanlang:",
        "btn_new": "Yangi murojaat",
        "btn_my": "Mening murojaatlarim",
        "btn_rules": "Qoidalar",
        "btn_lang": "Tilni ozgartirish",
        "btn_vol": "Volontyor bolish",
        "choose_vol": "Volontyorlik yonalishini tanlang:",
        "vol_contact": "Biz siz bilan boglanishimiz uchun raqamingizni qoldiring:",
        "vol_sent": "Volontyorlik arizangiz yuborildi!\n\nTez orada siz bilan boglanamiz. Rahmat!",
        "btn_chat": "Bizga yozing",
        "chat_started": "Biz bilan toghridan-toghri suhbat boshladingiz. Savolingizni yozing:",
        "chat_end_btn": "Suhbatni yakunlash",
        "chat_ended_u": "Suhbat yakunlandi. Menyuga qaytamiz.",
        "chat_ended_a": "Foydalanuvchi bilan suhbat yakunlandi.",
        "choose_contact": "Telefon raqamingizni qoldirmoqchimisiz?\n\nDiqqat: Anonim qolsangiz biz siz bilan boghlana olmaymiz.",
        "share_phone": "Raqamni ulashish",
        "stay_anon": "Anonim qolish",
        "anon_warning": "Siz anonimlikni tanladingiz.\nMurojaat uzatiladi, lekin biz siz bilan boghlana olmaymiz.",
        "choose_region": "Viloyatingizni tanlang:",
        "vol_region": "Viloyatingizni tanlang:",
        "send_appeal": "Murojaatingizni yozing\n\nMatn yozing bir nechta xabar yuborishingiz mumkin.\nRasm/video alohida yuboring.\n\nTayyor bolgach Murojaatni yuborish tugmasini bosing.",
        "submit_btn": "Murojaatni yuborish",
        "cancel_btn": "Bekor qilish",
        "thank_you": "Murojaatingiz qabul qilindi!\n\nKatta rahmat. Murojaatingizni korib chiqamiz.\n\nMening murojaatlarim bolimida javoblarni kuzatishingiz mumkin.",
        "media_received": "Fayl qabul qilindi. Davom eting yoki Murojaatni yuborish tugmasini bosing.",
        "text_added": "Matn qoshildi. Davom eting yoki Murojaatni yuborish tugmasini bosing.",
        "admin_appeal": "YANGI MUROJAAT",
        "admin_vol": "YANGI VOLONTYOR",
        "region_label": "Viloyat",
        "contact_label": "Kontakt",
        "anon_label": "Anonim",
        "message_label": "Murojaat",
        "vol_dir_label": "Yonalish",
        "no_message": "faqat media fayllar",
        "no_appeals": "Sizda hali murojaatlar yoq.",
        "your_appeals": "Sizning murojaatlaringiz:",
        "no_replies": "Hali javob yoq.",
        "reply_label": "Javob",
        "reply_received": "#{id}-murojaat javobingiz:\n\n{reply}",
        "rules": "BOTDAN FOYDALANISH QOIDALARI\n\n1. Taqiqlangan: sokinish, haqoratli sozlar.\n2. Taqiqlangan: spam, reklama, tahdidlar.\n3. Taqiqlangan: yolgon malumot.\n4. Taqiqlangan: botni suistemol qilish.\n\nQANDAY FOYDALANISH:\n- Yangi murojaat tugmasini bosing\n- Raqam qoldiring yoki anonim qoling\n- Viloyatni tanlang\n- Muammoni tasvirlang\n- Murojaatni yuborish tugmasini bosing\n\nQoidalarni buzish bloklashga olib keladi.",
        "blocked_perm": "Siz qoidalarni buzganingiz uchun doimiy ravishda bloklandingiz.",
        "blocked_temp": "Siz {until} gacha bloklangansiz.",
        "appeal_id": "Murojaat ID",
        "back": "Orqaga",
        "admin_wrote": "Javob: {text}",
    },
    "kk": {
        "welcome": "Xosh keldiniz!\n\nBul bot Ozbekistan puqaralarinin murajaatların qabıl etiw ushin.\n\nTildi tanlang:",
        "menu": "Bas menyu\n\nAmaldı tanlang:",
        "btn_new": "Jana murajaat",
        "btn_my": "Menin murajaatlarım",
        "btn_rules": "Qaydalar",
        "btn_lang": "Tildi ozgertiw",
        "btn_vol": "Volonter bolıw",
        "choose_vol": "Volonterlik bagdarın tanlang:",
        "vol_contact": "Nomernizdi qaldırın biz siz benen baylanısamız:",
        "vol_sent": "Volonterlik arzanız jiberildi!\n\nTez arada siz benen baylanısadı. Rahmet!",
        "btn_chat": "Bizge jazın",
        "chat_started": "Biz benen tuwrıdan-tuwrı suhbat bastadınız. Sawalınızdı jazın:",
        "chat_end_btn": "Suhbattı tamamlawlaw",
        "chat_ended_u": "Suhbat tamawlandı. Menyuga qaytamız.",
        "chat_ended_a": "Paydalanıwshı benen suhbat tamawlandı.",
        "choose_contact": "Telefon nomernizdi qaldırganız keleme?\n\nDıqqat: Anonim qalsanız biz siz benen baylanısa almaymız.",
        "share_phone": "Nomerni ulasıw",
        "stay_anon": "Anonim qalıw",
        "anon_warning": "Siz anonimlikti tanladınız.\nMurajaat jetkiziledi, biraq biz siz benen baylanısa almaymız.",
        "choose_region": "Regionınızdı tanlang:",
        "vol_region": "Regionınızdı tanlang:",
        "send_appeal": "Murajaatınızdı jazın\n\nMatn jazın birneshe xabar jibere alasız.\nSuwret/video boleksha jiberin.\n\nTayar bolganda Murajaat jiberiw tugmasin basın.",
        "submit_btn": "Murajaat jiberiw",
        "cancel_btn": "Biykar etiw",
        "thank_you": "Murajaatınız qabıl etildi!\n\nKop rahmet. Murajaatınızdı korib shıgamız.\n\nMenin murajaatlarım boliminde jawaplardı kore alasız.",
        "media_received": "Fayl qabıl etildi. Davom etin yaki Murajaat jiberiw tugmasin basın.",
        "text_added": "Matn qosıldı. Davom etin yaki Murajaat jiberiw tugmasin basın.",
        "admin_appeal": "JANA MURAJAAT",
        "admin_vol": "JANA VOLONTER",
        "region_label": "Region",
        "contact_label": "Baylanıs",
        "anon_label": "Anonim",
        "message_label": "Murajaat",
        "vol_dir_label": "Bagdar",
        "no_message": "tek media fayllar",
        "no_appeals": "Sizde halirshe murajaatlar joq.",
        "your_appeals": "Sizin murajaatlarınız:",
        "no_replies": "Halirshe jawap joq.",
        "reply_label": "Jawap",
        "reply_received": "#{id}-murajaat jawabınız:\n\n{reply}",
        "rules": "BOTTAN PAYDALANIW QAYDALARI\n\n1. Tıyım: sokinish, haqoretli sozler.\n2. Tıyım: spam, reklama, qorqıtıwlar.\n3. Tıyım: jalgan maglıwmat.\n4. Tıyım: bottı qıyanetlep paydalanıw.\n\nQALAYINSHA PAYDALANIW:\n- Jana murajaat tugmasin basın\n- Nomer qaldırın yaki anonim qalın\n- Regionınızdı tanlang\n- Maseleni tasvirlen\n- Murajaat jiberiw tugmasin basın\n\nQaydaların bozıw bloklashga alıp keledi.",
        "blocked_perm": "Siz qaydaların bozganınız ushin mangi bloclandınız.",
        "blocked_temp": "Siz {until} ga shekem bloclandınız.",
        "appeal_id": "Murajaat ID",
        "back": "Artqa",
        "admin_wrote": "Jawap: {text}",
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

def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇺🇿 O'zbek",  callback_data="lang_uz")],
        [InlineKeyboardButton("🏳️ Qaraqalpaqsha", callback_data="lang_kk")],
    ])

def menu_kb(lang):
    return ReplyKeyboardMarkup([
        [KeyboardButton("✍️ " + T(lang,"btn_new")),  KeyboardButton("📋 " + T(lang,"btn_my"))],
        [KeyboardButton("🤝 " + T(lang,"btn_vol")),  KeyboardButton("📜 " + T(lang,"btn_rules"))],
        [KeyboardButton("🌐 " + T(lang,"btn_lang"))],
    ], resize_keyboard=True)

def contact_kb(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 " + T(lang,"share_phone"), callback_data="contact_phone")],
        [InlineKeyboardButton("🙈 " + T(lang,"stay_anon"),   callback_data="contact_anon")],
    ])

def region_kb(prefix="reg"):
    rows = []
    for i in range(0, len(REGIONS), 2):
        row = [InlineKeyboardButton(REGIONS[i], callback_data=f"{prefix}_{i}")]
        if i+1 < len(REGIONS):
            row.append(InlineKeyboardButton(REGIONS[i+1], callback_data=f"{prefix}_{i+1}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def submit_kb(lang):
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ " + T(lang,"submit_btn"))],
        [KeyboardButton("❌ " + T(lang,"cancel_btn"))],
    ], resize_keyboard=True)

def vol_dir_kb(lang):
    emojis = {"vol_kids":"🧸","vol_elder":"👴","vol_eco":"🌿","vol_edu":"🎓","vol_it":"💻"}
    names_ru = {
        "vol_kids":"Детские дома и интернаты","vol_elder":"Помощь пожилым людям",
        "vol_eco":"Эко-акции и уборка (Хашар)","vol_edu":"Обучение и тьюторство",
        "vol_it":"IT-волонтёрство (Pro Bono)"
    }
    names_uz = {
        "vol_kids":"Bolalar uylari va internatlar","vol_elder":"Keksalarga yordam",
        "vol_eco":"Eko-aksiyalar (Hashar)","vol_edu":"Ta'lim va tyutorlik",
        "vol_it":"IT-volontyorlik (Pro Bono)"
    }
    names_kk = {
        "vol_kids":"Balalar uyleri","vol_elder":"Qarilarğa jardem",
        "vol_eco":"Eko-aksiyalar","vol_edu":"Oqıtıw",
        "vol_it":"IT-volontyorlik"
    }
    name_map = {"ru": names_ru, "uz": names_uz, "kk": names_kk}
    names = name_map.get(lang, names_ru)
    rows = []
    for key in ["vol_kids","vol_elder","vol_eco","vol_edu","vol_it"]:
        rows.append([InlineKeyboardButton(emojis[key] + " " + names[key], callback_data=key)])
    rows.append([InlineKeyboardButton("⬅️ " + T(lang,"back"), callback_data="vol_back")])
    return InlineKeyboardMarkup(rows)

def admin_kb_fn(aid, uid, kind="appeal"):
    prefix = "arep" if kind == "appeal" else "vrep"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить / открыть чат", callback_data=f"{prefix}_{aid}_{uid}")],
        [InlineKeyboardButton("⏱ 1 час", callback_data=f"block_{uid}_1h"),
         InlineKeyboardButton("⏱ 3 часа", callback_data=f"block_{uid}_3h")],
        [InlineKeyboardButton("📅 1 день", callback_data=f"block_{uid}_1d"),
         InlineKeyboardButton("📅 1 неделя", callback_data=f"block_{uid}_1w")],
        [InlineKeyboardButton("🚫 Заблокировать навсегда", callback_data=f"block_{uid}_perm")],
    ])

def chat_kb(lang):
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔚 " + T(lang,"chat_end_btn"))]],
        resize_keyboard=True
    )

async def send_to_targets(bot, caption, media_ids, kb):
    targets = [t for t in [ADMIN_ID, GROUP_ID] if t]
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

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    blocked, until = check_block(uid)
    if blocked:
        lang = get_lang(uid)
        msg = T(lang,"blocked_perm") if until == "permanent" else T(lang,"blocked_temp").format(until=until)
        await update.message.reply_text(msg)
        return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(TEXTS["ru"]["welcome"], reply_markup=lang_kb())
    return LANGUAGE

async def on_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = {"lang_ru":"ru","lang_uz":"uz","lang_kk":"kk"}.get(q.data,"ru")
    ctx.user_data["lang"] = lang
    user_languages[q.from_user.id] = lang
    await q.edit_message_text(T(lang,"menu"))
    await q.message.reply_text(T(lang,"menu"), reply_markup=menu_kb(lang))
    return MENU

async def on_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = ctx.user_data.get("lang", get_lang(uid))
    text = update.message.text

    blocked, until = check_block(uid)
    if blocked:
        msg = T(lang,"blocked_perm") if until == "permanent" else T(lang,"blocked_temp").format(until=until)
        await update.message.reply_text(msg)
        return MENU

    if T(lang,"btn_new") in text:
        await update.message.reply_text(T(lang,"choose_contact"), reply_markup=contact_kb(lang))
        return CONTACT

    if T(lang,"btn_vol") in text:
        await update.message.reply_text(T(lang,"choose_vol"), reply_markup=vol_dir_kb(lang))
        return VOL_TYPE

    if T(lang,"btn_my") in text:
        user_appeals = [(k,v) for k,v in appeals_db.items() if v["user_id"] == uid]
        if not user_appeals:
            await update.message.reply_text(T(lang,"no_appeals"))
            return MENU
        await update.message.reply_text(T(lang,"your_appeals"))
        for aid, ap in sorted(user_appeals):
            preview = (ap.get("text") or "")[:80]
            msg = f"#{aid} | {ap['date']}\n{ap['region']}\n{preview or T(lang,'no_message')}"
            if ap.get("replies"):
                for r in ap["replies"]:
                    msg += f"\n\n{T(lang,'reply_label')}: {r}"
            else:
                msg += f"\n\n{T(lang,'no_replies')}"
            await update.message.reply_text(msg)
        return MENU

    if T(lang,"btn_rules") in text:
        await update.message.reply_text(T(lang,"rules"))
        return MENU

    if T(lang,"btn_lang") in text:
        await update.message.reply_text(TEXTS["ru"]["welcome"], reply_markup=lang_kb())
        return LANGUAGE

    if uid in user_chat_mode:
        end_text = "🔚 " + T(lang,"chat_end_btn")
        if end_text in text:
            del user_chat_mode[uid]
            if ADMIN_ID in admin_chat_target and admin_chat_target[ADMIN_ID] == uid:
                del admin_chat_target[ADMIN_ID]
                try:
                    await ctx.bot.send_message(ADMIN_ID, "Чат с пользователем завершён.")
                except: pass
            await update.message.reply_text(T(lang,"chat_ended_u"), reply_markup=menu_kb(lang))
            return MENU
        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"[Чат от {update.effective_user.full_name} | {uid}]\n{text}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 Ответить в чат", callback_data=f"chat_{uid}")
                ]])
            )
        except Exception as e:
            logger.error(f"Chat forward failed: {e}")
        return MENU

    return MENU

async def on_vol_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))
    if q.data == "vol_back":
        await q.edit_message_text(T(lang,"menu"))
        await q.message.reply_text(T(lang,"menu"), reply_markup=menu_kb(lang))
        return MENU
    emojis = {"vol_kids":"🧸","vol_elder":"👴","vol_eco":"🌿","vol_edu":"🎓","vol_it":"💻"}
    names_ru = {"vol_kids":"Детские дома и интернаты","vol_elder":"Помощь пожилым людям","vol_eco":"Эко-акции и уборка (Хашар)","vol_edu":"Обучение и тьюторство","vol_it":"IT-волонтёрство (Pro Bono)"}
    names_uz = {"vol_kids":"Bolalar uylari va internatlar","vol_elder":"Keksalarga yordam","vol_eco":"Eko-aksiyalar (Hashar)","vol_edu":"Ta'lim va tyutorlik","vol_it":"IT-volontyorlik (Pro Bono)"}
    names_kk = {"vol_kids":"Balalar uyleri","vol_elder":"Qarilarğa jardem","vol_eco":"Eko-aksiyalar","vol_edu":"Oqıtıw","vol_it":"IT-volontyorlik"}
    name_map = {"ru": names_ru, "uz": names_uz, "kk": names_kk}
    name = emojis.get(q.data,"") + " " + name_map.get(lang, names_ru).get(q.data, q.data)
    ctx.user_data["vol_direction"] = name
    await q.edit_message_text(f"Tvoy vybor: {name}")
    await q.message.reply_text(T(lang,"vol_contact"), reply_markup=contact_kb(lang))
    return VOL_REGION

async def on_vol_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", get_lang(q.from_user.id))
    idx = int(q.data.split("_")[1])
    ctx.user_data["vol_region"] = REGIONS[idx]
    await q.edit_message_text(f"✅ {REGIONS[idx]}")
    return await _submit_volunteer(q.message, ctx, q.from_user)

async def _submit_volunteer(message, ctx, user):
    lang      = ctx.user_data.get("lang", get_lang(user.id))
    direction = ctx.user_data.get("vol_direction","—")
    region    = ctx.user_data.get("vol_region","—")
    contact   = ctx.user_data.get("contact")
    aid       = new_aid()
    date_str  = datetime.now().strftime("%d.%m.%Y %H:%M")
    appeals_db[aid] = {
        "user_id": user.id,"region": region,"contact": contact,
        "text": direction,"media": [],"date": date_str,
        "replies": [],"lang": lang,"type": "volunteer",
    }
    contact_str = ("+" + contact) if contact else T(lang,"anon_label")
    lang_names  = {"ru":"Русский","uz":"O'zbek","kk":"Qaraqalpaqsha"}
    caption = (
        f"{T(lang,'admin_vol')}\n\n"
        f"Пользователь: {user.full_name} (@{user.username or '—'}) [{user.id}]\n"
        f"ID: #{aid}\n"
        f"{T(lang,'vol_dir_label')}: {direction}\n"
        f"{T(lang,'region_label')}: {region}\n"
        f"{T(lang,'contact_label')}: {contact_str}\n"
        f"Язык: {lang_names.get(lang,lang)}\n"
        f"Дата: {date_str}"
    )
    await send_to_targets(ctx.bot, caption, [], admin_kb_fn(aid, user.id, kind="vol"))
    vol_kb = ReplyKeyboardMarkup([
        [KeyboardButton("💬 " + T(lang,"btn_chat"))],
        [KeyboardButton("🏠 " + T(lang,"menu").split("\n")[0])],
    ], resize_keyboard=True)
    await message.reply_text(T(lang,"vol_sent"), reply_markup=vol_kb)
    user_chat_mode[user.id] = True
    ctx.user_data.clear()
    ctx.user_data["lang"] = lang
    return MENU

async def on_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang   = ctx.user_data.get("lang", get_lang(q.from_user.id))
    is_vol = "vol_direction" in ctx.user_data
    if q.data == "contact_phone":
        btn_labels = {"ru":"Отправить номер","uz":"Raqam yuborish","kk":"Nomerni jiberiw"}
        phone_kb = ReplyKeyboardMarkup(
            [[KeyboardButton(btn_labels.get(lang,"Отправить номер"), request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        prompts = {"ru":"Нажмите кнопку ниже:","uz":"Tugmani bosing:","kk":"Tugmasin basın:"}
        await q.edit_message_text(prompts.get(lang,""))
        await q.message.reply_text("👇", reply_markup=phone_kb)
        return VOL_REGION if is_vol else REGION
    else:
        ctx.user_data["contact"] = None
        await q.edit_message_text(T(lang,"anon_warning"))
        if is_vol:
            await q.message.reply_text(T(lang,"vol_region"), reply_markup=region_kb("vreg"))
            return VOL_REGION
        else:
            await q.message.reply_text(T(lang,"choose_region"), reply_markup=region_kb("reg"))
            return REGION

async def on_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang   = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    ctx.user_data["contact"] = update.message.contact.phone_number
    is_vol = "vol_direction" in ctx.user_data
    if is_vol:
        await update.message.reply_text(T(lang,"vol_region"), reply_markup=region_kb("vreg"))
        return VOL_REGION
    else:
        await update.message.reply_text(T(lang,"choose_region"), reply_markup=region_kb("reg"))
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
    await q.message.reply_text(T(lang,"send_appeal"), reply_markup=submit_kb(lang))
    return APPEAL

async def on_appeal_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang   = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    text   = update.message.text
    submit = "✅ " + T(lang,"submit_btn")
    cancel = "❌ " + T(lang,"cancel_btn")
    if submit in text:
        return await do_submit(update, ctx)
    if cancel in text:
        ctx.user_data["lang"] = lang
        await update.message.reply_text(T(lang,"menu"), reply_markup=menu_kb(lang))
        return MENU
    ctx.user_data.setdefault("text_parts",[]).append(text)
    await update.message.reply_text(T(lang,"text_added"))
    return APPEAL

async def on_appeal_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang      = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    media_ids = ctx.user_data.setdefault("media_ids",[])
    if update.message.photo:
        media_ids.append({"type":"photo","id":update.message.photo[-1].file_id})
    elif update.message.video:
        media_ids.append({"type":"video","id":update.message.video.file_id})
    elif update.message.document:
        media_ids.append({"type":"document","id":update.message.document.file_id})
    if update.message.caption:
        ctx.user_data.setdefault("text_parts",[]).append(update.message.caption)
    await update.message.reply_text(T(lang,"media_received"))
    return APPEAL

async def do_submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang       = ctx.user_data.get("lang", get_lang(update.effective_user.id))
    region     = ctx.user_data.get("region","—")
    contact    = ctx.user_data.get("contact")
    text_parts = ctx.user_data.get("text_parts",[])
    full_text  = "\n\n".join(text_parts) if text_parts else ""
    media_ids  = ctx.user_data.get("media_ids",[])
    user       = update.effective_user
    aid        = new_aid()
    date_str   = datetime.now().strftime("%d.%m.%Y %H:%M")
    appeals_db[aid] = {
        "user_id": user.id,"region": region,"contact": contact,
        "text": full_text,"media": media_ids,"date": date_str,
        "replies": [],"lang": lang,"type": "appeal",
    }
    contact_str = ("+" + contact) if contact else T(lang,"anon_label")
    lang_names  = {"ru":"Русский","uz":"O'zbek","kk":"Qaraqalpaqsha"}
    caption = (
        f"{T(lang,'admin_appeal')}\n\n"
        f"Пользователь: {user.full_name} (@{user.username or '—'}) [{user.id}]\n"
        f"{T(lang,'appeal_id')}: #{aid}\n"
        f"{T(lang,'region_label')}: {region}\n"
        f"{T(lang,'contact_label')}: {contact_str}\n"
        f"Язык: {lang_names.get(lang,lang)}\n"
        f"Дата: {date_str}\n\n"
        f"{T(lang,'message_label')}:\n"
        f"{full_text if full_text else T(lang,'no_message')}"
    )
    await send_to_targets(ctx.bot, caption, media_ids, admin_kb_fn(aid, user.id, kind="appeal"))
    await update.message.reply_text(T(lang,"thank_you"), reply_markup=menu_kb(lang))
    ctx.user_data.clear()
    ctx.user_data["lang"] = lang
    return MENU

async def on_admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Нет доступа", show_alert=True)
        return
    await q.answer()
    data = q.data

    if data.startswith("arep_") or data.startswith("vrep_"):
        parts = data.split("_")
        aid   = int(parts[1])
        uid   = int(parts[2])
        pending_reply[ADMIN_ID]    = {"appeal_id": aid, "user_id": uid}
        admin_chat_target[ADMIN_ID] = uid
        user_chat_mode[uid]         = True
        lang = user_languages.get(uid,"ru")
        try:
            await ctx.bot.send_message(uid, T(lang,"chat_started"), reply_markup=chat_kb(lang))
        except Exception as e:
            logger.error(f"Chat start failed: {e}")
        await q.message.reply_text(
            f"Чат открыт с пользователем {uid}.\nВсё что пишете — уходит ему напрямую.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔚 Завершить чат", callback_data=f"endchat_{uid}")
            ]])
        )
        return

    if data.startswith("chat_"):
        uid = int(data.split("_")[1])
        admin_chat_target[ADMIN_ID] = uid
        user_chat_mode[uid]         = True
        lang = user_languages.get(uid,"ru")
        try:
            await ctx.bot.send_message(uid, T(lang,"chat_started"), reply_markup=chat_kb(lang))
        except Exception as e:
            logger.error(f"Chat start failed: {e}")
        await q.message.reply_text(
            f"Чат открыт с {uid}. Пишите — уходит пользователю.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔚 Завершить чат", callback_data=f"endchat_{uid}")
            ]])
        )
        return

    if data.startswith("endchat_"):
        uid = int(data.split("_")[1])
        user_chat_mode.pop(uid, None)
        admin_chat_target.pop(ADMIN_ID, None)
        lang = user_languages.get(uid,"ru")
        try:
            await ctx.bot.send_message(uid, T(lang,"chat_ended_u"), reply_markup=menu_kb(lang))
        except: pass
        await q.message.reply_text("Чат с пользователем завершён.")
        return

    if data.startswith("block_"):
        parts = data.split("_")
        uid   = int(parts[1])
        dur   = parts[2]
        durations = {"1h":3600,"3h":10800,"1d":86400,"1w":604800,"perm":0}
        labels    = {"1h":"1 час","3h":"3 часа","1d":"1 день","1w":"1 неделю","perm":"навсегда"}
        secs  = durations.get(dur,3600)
        label = labels.get(dur,dur)
        if secs == 0:
            blocked_users[uid] = 0
            until_str = "навсегда"
        else:
            until_ts = time.time() + secs
            blocked_users[uid] = until_ts
            until_str = datetime.fromtimestamp(until_ts).strftime("%d.%m.%Y %H:%M")
        user_lang = user_languages.get(uid,"ru")
        try:
            msg = T(user_lang,"blocked_perm") if secs == 0 else T(user_lang,"blocked_temp").format(until=until_str)
            await ctx.bot.send_message(uid, msg)
        except Exception as e:
            logger.error(f"Block notify failed: {e}")
        await q.message.reply_text(f"Пользователь {uid} заблокирован на {label}.")

async def on_admin_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    text = update.message.text or ""
    if ADMIN_ID in admin_chat_target:
        target_uid = admin_chat_target[ADMIN_ID]
        user_lang  = user_languages.get(target_uid,"ru")
        try:
            await ctx.bot.send_message(target_uid, T(user_lang,"admin_wrote").format(text=text))
            await update.message.reply_text("✅ Отправлено")
        except Exception as e:
            logger.error(f"Admin chat send failed: {e}")
            await update.message.reply_text("❌ Не удалось отправить")
        if ADMIN_ID in pending_reply:
            info = pending_reply.pop(ADMIN_ID)
            aid  = info["appeal_id"]
            if aid in appeals_db:
                appeals_db[aid]["replies"].append(text)
        return
    if ADMIN_ID in pending_reply:
        info       = pending_reply.pop(ADMIN_ID)
        aid        = info["appeal_id"]
        target_uid = info["user_id"]
        user_lang  = appeals_db.get(aid,{}).get("lang", user_languages.get(target_uid,"ru"))
        if aid in appeals_db:
            appeals_db[aid]["replies"].append(text)
        try:
            await ctx.bot.send_message(target_uid, T(user_lang,"reply_received").format(id=aid,reply=text))
            await update.message.reply_text(f"✅ Ответ отправлен (#{aid}).")
        except Exception as e:
            logger.error(f"Reply send failed: {e}")
            await update.message.reply_text("❌ Не удалось отправить.")

async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Error:", exc_info=ctx.error)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE:   [CallbackQueryHandler(on_language, pattern="^lang_")],
            MENU:       [MessageHandler(filters.TEXT & ~filters.COMMAND, on_menu)],
            CONTACT:    [CallbackQueryHandler(on_contact,  pattern="^contact_")],
            REGION:     [
                CallbackQueryHandler(on_region, pattern="^reg_"),
                MessageHandler(filters.CONTACT, on_phone),
            ],
            APPEAL:     [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_appeal_text),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, on_appeal_media),
            ],
            VOL_TYPE:   [CallbackQueryHandler(on_vol_type, pattern="^(vol_kids|vol_elder|vol_eco|vol_edu|vol_it|vol_back)$")],
            VOL_REGION: [
                CallbackQueryHandler(on_vol_region, pattern="^vreg_"),
                CallbackQueryHandler(on_contact,    pattern="^contact_"),
                MessageHandler(filters.CONTACT,     on_phone),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(on_admin_callback, pattern="^(arep_|vrep_|block_|chat_|endchat_)"))
    if ADMIN_ID:
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
            on_admin_message
        ))
    app.add_error_handler(on_error)
    logger.info("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
