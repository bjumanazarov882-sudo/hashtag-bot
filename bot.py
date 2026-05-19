"""
╔══════════════════════════════════════════════════════════════╗
║         𝗨𝗻𝗶𝘃𝗲𝗿𝘀𝗮𝗹 𝗛𝗮𝘀𝗵𝘁𝗮𝗴 𝗕𝗼𝘁 — 𝗙𝘂𝗹𝗹 𝗩𝗲𝗿𝘀𝗶𝗼𝗻             ║
║  Platform: Telegram                                          ║
║  Kutubxonalar:                                               ║
║    pip install pyTelegramBotAPI yt-dlp schedule              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import telebot
import yt_dlp
import re
import json
import logging
import tempfile
import threading
import schedule
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from telebot import types

# ═══════════════════════════════════════════════════════════════
# ⚙️  SOZLAMALAR
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN  = os.environ.get("8944587981:AAHTSU2Md2DKsa3Rs09ehM1ooKZGvHALJ1U")
KANAL      = "@ixo_uzz"
ADMIN_IDS  = [6391668377]   # <-- O'z Telegram ID'ingizni yozing

USERS_FILE           = "users.json"
STATS_FILE           = "stats.json"
BLOCKED_FILE         = "blocked.json"
CUSTOM_HASHTAGS_FILE = "custom_hashtags.json"
SCHEDULED_FILE       = "scheduled.json"
ADMINS_FILE          = "admins.json"
FAVORITES_FILE       = "favorites.json"
ACTIVITY_FILE        = "activity.json"
LOG_FILE             = "bot.log"

# Anti-spam: soniyada nechta xabar
SPAM_LIMIT    = 5   # xabar soni
SPAM_WINDOW   = 10  # soniya

# ═══════════════════════════════════════════════════════════════
# 📝  LOGGING
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 🤖  BOT
# ═══════════════════════════════════════════════════════════════

bot = telebot.TeleBot(BOT_TOKEN)

BOT_TOXTATILGAN = False
TEXNIK_XABAR    = "⚙️ Bot hozir texnik ishlar uchun to'xtatilgan. Tez orada qaytamiz!"

# Anti-spam xotirasi
spam_tracker = defaultdict(list)   # {user_id: [timestamp, ...]}
spam_blocked = {}                  # {user_id: unblock_time}

# ═══════════════════════════════════════════════════════════════
# 👥  FOYDALANUVCHILAR
# ═══════════════════════════════════════════════════════════════

def json_yukla(fayl, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(fayl):
            with open(fayl, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.error(f"JSON yuklash xatosi ({fayl}): {e}")
    return default

def json_saqlash(fayl, data):
    try:
        with open(fayl, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"JSON saqlash xatosi ({fayl}): {e}")

def users_yukla():       return json_yukla(USERS_FILE, {})
def users_saqlash(d):    json_saqlash(USERS_FILE, d)
def blocked_yukla():     return json_yukla(BLOCKED_FILE, {})
def blocked_saqlash(d):  json_saqlash(BLOCKED_FILE, d)
def stats_yukla():       return json_yukla(STATS_FILE, {"kunlik": {}, "yuklamalar": 0, "hashtag_sorov": 0})
def stats_saqlash(d):    json_saqlash(STATS_FILE, d)
def admins_yukla():      return json_yukla(ADMINS_FILE, {})
def admins_saqlash(d):   json_saqlash(ADMINS_FILE, d)
def favorites_yukla():   return json_yukla(FAVORITES_FILE, {})
def favorites_saqlash(d):json_saqlash(FAVORITES_FILE, d)
def activity_yukla():    return json_yukla(ACTIVITY_FILE, {})
def activity_saqlash(d): json_saqlash(ACTIVITY_FILE, d)
def scheduled_yukla():   return json_yukla(SCHEDULED_FILE, [])
def scheduled_saqlash(d):json_saqlash(SCHEDULED_FILE, d)

def foydalanuvchi_qoshish(user):
    users = users_yukla()
    uid   = str(user.id)
    if uid not in users:
        users[uid] = {
            "id":       user.id,
            "ism":      user.first_name or "",
            "username": user.username or "",
            "qoshilgan": str(date.today()),
            "til":      "uz"
        }
        users_saqlash(users)
        log.info(f"Yangi foydalanuvchi: {user.id} (@{user.username})")
    return users[uid]

def faoliyat_yangilash(user_id):
    activity = activity_yukla()
    activity[str(user_id)] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    activity_saqlash(activity)

def barcha_userlar():
    users   = users_yukla()
    blocked = blocked_yukla()
    return [v["id"] for k, v in users.items() if k not in blocked]

def foydalanuvchi_qidir(qidiruv):
    users = users_yukla()
    q     = str(qidiruv).strip().lstrip("@")
    for uid, v in users.items():
        if uid == q or v.get("username", "") == q:
            return v
    return None

def users_txt_export():
    users    = users_yukla()
    blocked  = blocked_yukla()
    activity = activity_yukla()
    lines    = ["ID           | ISM                | USERNAME          | QOSHILGAN  | OXIRGI FAOLLIK      | HOLAT\n" + "="*95]
    for uid, v in users.items():
        holat  = "🚫 Bloklangan" if uid in blocked else "✅ Faol"
        oxirgi = activity.get(uid, "-")
        lines.append(
            f"{str(v['id']):<13}| {v.get('ism','?'):<19}| @{v.get('username','-'):<18}| {v.get('qoshilgan','-'):<11}| {oxirgi:<20}| {holat}"
        )
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════
# 🛡️  ADMIN TIZIMI
# ═══════════════════════════════════════════════════════════════

def admin_mi(user_id):
    if user_id in ADMIN_IDS:
        return True
    admins = admins_yukla()
    return str(user_id) in admins

def super_admin_mi(user_id):
    return user_id in ADMIN_IDS

def admin_qosh(user_id, ism="", username=""):
    admins = admins_yukla()
    admins[str(user_id)] = {
        "id":       user_id,
        "ism":      ism,
        "username": username,
        "qoshilgan": str(date.today())
    }
    admins_saqlash(admins)

def admin_ochir(user_id):
    admins = admins_yukla()
    uid    = str(user_id)
    if uid in admins:
        del admins[uid]
        admins_saqlash(admins)
        return True
    return False

def admin_royxat():
    admins = admins_yukla()
    lines  = []
    for uid, v in admins.items():
        lines.append(f"• `{v['id']}` — {v.get('ism','-')} | @{v.get('username','-')} | {v.get('qoshilgan','-')}")
    return lines

# ═══════════════════════════════════════════════════════════════
# 🚫  BLOKLASH
# ═══════════════════════════════════════════════════════════════

def bloklangan_mi(user_id):
    return str(user_id) in blocked_yukla()

def foydalanuvchi_blokla(user_id, sabab="Admin tomonidan bloklandi"):
    blocked = blocked_yukla()
    users   = users_yukla()
    uid     = str(user_id)
    blocked[uid] = {
        "id":       user_id,
        "ism":      users.get(uid, {}).get("ism", "Noma'lum"),
        "username": users.get(uid, {}).get("username", ""),
        "sabab":    sabab,
        "sana":     str(date.today())
    }
    blocked_saqlash(blocked)
    log.info(f"Bloklandi: {user_id} — {sabab}")

def foydalanuvchi_blokdan_chiqar(user_id):
    blocked = blocked_yukla()
    uid = str(user_id)
    if uid in blocked:
        del blocked[uid]
        blocked_saqlash(blocked)
        log.info(f"Blokdan chiqarildi: {user_id}")
        return True
    return False

# ═══════════════════════════════════════════════════════════════
# ⚡  ANTI-SPAM
# ═══════════════════════════════════════════════════════════════

def spam_tekshir(user_id):
    if admin_mi(user_id):
        return False
    now = time.time()
    uid = str(user_id)
    if uid in spam_blocked:
        if now < spam_blocked[uid]:
            return True
        else:
            del spam_blocked[uid]
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t < SPAM_WINDOW]
    spam_tracker[uid].append(now)
    if len(spam_tracker[uid]) > SPAM_LIMIT:
        spam_blocked[uid] = now + 60
        log.warning(f"Spam aniqlandi: {user_id}")
        return True
    return False

# ═══════════════════════════════════════════════════════════════
# 📊  STATISTIKA
# ═══════════════════════════════════════════════════════════════

def yuklab_olish_hisob():
    stats  = stats_yukla()
    stats["yuklamalar"] = stats.get("yuklamalar", 0) + 1
    bugun  = str(date.today())
    kunlik = stats.get("kunlik", {})
    kunlik[bugun] = kunlik.get(bugun, 0) + 1
    stats["kunlik"] = kunlik
    stats_saqlash(stats)

def hashtag_sorov_hisob():
    stats = stats_yukla()
    stats["hashtag_sorov"] = stats.get("hashtag_sorov", 0) + 1
    stats_saqlash(stats)

def statistika_matn():
    stats    = stats_yukla()
    users    = users_yukla()
    blocked  = blocked_yukla()
    admins   = admins_yukla()
    activity = activity_yukla()
    bugun    = str(date.today())
    kunlik   = stats.get("kunlik", {})

    haftalik = sum(v for k, v in kunlik.items() if k >= str(date.today() - timedelta(days=7)))
    oylik    = sum(v for k, v in kunlik.items() if k >= str(date.today() - timedelta(days=30)))

    grafik = ""
    for i in range(6, -1, -1):
        kun   = str(date.today() - timedelta(days=i))
        son   = kunlik.get(kun, 0)
        bar   = "█" * min(son, 10) + "░" * max(0, 10 - min(son, 10))
        label = kun[5:]
        grafik += f"`{label}` {bar} {son}\n"

    oxirgi_faol = sorted(activity.items(), key=lambda x: x[1], reverse=True)[:5]
    faol_matn   = ""
    for uid, vaqt in oxirgi_faol:
        u = users.get(uid, {})
        faol_matn += f"• {u.get('ism',uid)} — {vaqt}\n"

    return (
        "📊 *𝗧𝗼'𝗹𝗶𝗾 𝗦𝘁𝗮𝘁𝗶𝘀𝘁𝗶𝗸𝗮*\n\n"
        f"👥 Jami foydalanuvchilar: *{len(users)}* ta\n"
        f"🛡 Adminlar: *{len(admins) + len(ADMIN_IDS)}* ta\n"
        f"🚫 Bloklangan: *{len(blocked)}* ta\n"
        f"✅ Faol: *{len(users) - len(blocked)}* ta\n\n"
        f"📥 Jami yuklamalar: *{stats.get('yuklamalar', 0)}* ta\n"
        f"🏷 Hashtag so'rovlar: *{stats.get('hashtag_sorov', 0)}* ta\n\n"
        f"📅 Bugungi yuklamalar: *{kunlik.get(bugun, 0)}* ta\n"
        f"📆 Haftalik: *{haftalik}* ta\n"
        f"🗓 Oylik: *{oylik}* ta\n\n"
        f"📈 *Oxirgi 7 kun:*\n{grafik}\n"
        f"⚡ *Oxirgi faol:*\n{faol_matn or 'Maʼlumot yoʼq'}\n"
        f"🤖 Bot holati: {'🔴 To\\'xtatilgan' if BOT_TOXTATILGAN else '🟢 Ishlayapti'}"
    )

def kunlik_hisobot():
    matn = f"🌅 *Kunlik hisobot — {date.today()}*\n\n" + statistika_matn()
    for aid in ADMIN_IDS:
        try:
            bot.send_message(aid, matn, parse_mode="Markdown")
        except Exception as e:
            log.error(f"Hisobot yuborishda xato ({aid}): {e}")
    admins = admins_yukla()
    for uid in admins:
        try:
            bot.send_message(int(uid), matn, parse_mode="Markdown")
        except:
            pass

# ═══════════════════════════════════════════════════════════════
# ⏰  REJALASHTIRILGAN XABARLAR
# ═══════════════════════════════════════════════════════════════

def rejalashtirilgan_xabar_yuborish(vaqt, xabar):
    def job():
        userlar   = barcha_userlar()
        yuborildi = 0
        for user_id in userlar:
            try:
                bot.send_message(user_id, f"📢 *Yangilik:*\n\n{xabar}", parse_mode="Markdown")
                yuborildi += 1
            except:
                pass
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"✅ Rejalashtirilgan xabar yuborildi!\n👥 {yuborildi} ta foydalanuvchiga.")
            except:
                pass
        return schedule.CancelJob

    schedule.every().day.at(vaqt).do(job)
    data = scheduled_yukla()
    data.append({"vaqt": vaqt, "xabar": xabar, "sana": str(date.today())})
    scheduled_saqlash(data)

def schedule_runner():
    schedule.every().day.at("08:00").do(kunlik_hisobot)
    while True:
        schedule.run_pending()
        time.sleep(30)

# ═══════════════════════════════════════════════════════════════
# ⭐  SEVIMLILAR
# ═══════════════════════════════════════════════════════════════

def sevimli_qosh(user_id, kategoriya_kodi, indeks):
    favs = favorites_yukla()
    uid  = str(user_id)
    if uid not in favs:
        favs[uid] = []
    kalit = f"{kategoriya_kodi}_{indeks}"
    if kalit not in favs[uid]:
        favs[uid].append(kalit)
        favorites_saqlash(favs)
        return True
    return False

def sevimli_ochir(user_id, kalit):
    favs = favorites_yukla()
    uid  = str(user_id)
    if uid in favs and kalit in favs[uid]:
        favs[uid].remove(kalit)
        favorites_saqlash(favs)
        return True
    return False

def sevimlilar_royxat(user_id):
    favs   = favorites_yukla()
    uid    = str(user_id)
    barcha = barcha_hashtags()
    items  = []
    for kalit in favs.get(uid, []):
        qismlar = kalit.split("_", 1)
        if len(qismlar) == 2:
            kod, indeks = qismlar[0], int(qismlar[1])
            if kod in barcha and indeks < len(barcha[kod]["taglar"]):
                items.append({
                    "kalit":  kalit,
                    "nom":    barcha[kod]["nomi"],
                    "taglar": barcha[kod]["taglar"][indeks]
                })
    return items

# ═══════════════════════════════════════════════════════════════
# 💾  BACKUP
# ═══════════════════════════════════════════════════════════════

def backup_yaratish():
    import zipfile
    fayllar = [USERS_FILE, STATS_FILE, BLOCKED_FILE,
               CUSTOM_HASHTAGS_FILE, SCHEDULED_FILE, ADMINS_FILE,
               FAVORITES_FILE, ACTIVITY_FILE]
    zip_nomi = tempfile.mktemp(suffix=".zip")
    with zipfile.ZipFile(zip_nomi, "w") as zf:
        for f in fayllar:
            if os.path.exists(f):
                zf.write(f)
        if os.path.exists(LOG_FILE):
            zf.write(LOG_FILE)
    return zip_nomi

# ═══════════════════════════════════════════════════════════════
# 🏷️  HASHTAG KUTUBXONASI
# ═══════════════════════════════════════════════════════════════

HASHTAGS = {
    "biznes": {
        "nomi": "💼 𝗕𝗶𝘇𝗻𝗲𝘀 𝘃𝗮 𝗦𝗮𝘃𝗱𝗼",
        "taglar": [
            "#biznes #savdo #startup #tadbirkorlik #investitsiya",
            "#ecommerce #onlinebiznes #daromad #moliya #kapital",
            "#marketing #reklama #brend #mijozlar #sotish",
            "#b2b #b2c #sheriklik #hamkorlik #bitim",
            "#import #eksport #logistika #yetkazib_berish #ombor",
        ]
    },
    "lifestyle": {
        "nomi": "🌟 𝗟𝗶𝗳𝗲𝘀𝘁𝘆𝗹𝗲 𝘃𝗮 𝗕𝗹𝗼𝗴",
        "taglar": [
            "#lifestyle #hayot #motivatsiya #ilhom #muvaffaqiyat",
            "#blog #blogger #content #ijod #yaratuvchilik",
            "#travel #sayohat #dunyo #kashfiyot #adventure",
            "#fashion #moda #stil #trend #looks",
            "#fitness #sport #sog_lom #energia #harakat",
        ]
    },
    "talim": {
        "nomi": "📚 𝗧𝗮'𝗹𝗶𝗺 𝘃𝗮 𝗞𝘂𝗿𝘀",
        "taglar": [
            "#talim #kurs #onlinekurs #dars #oqish",
            "#dasturlash #programming #IT #texnologiya #kod",
            "#ingliz_tili #til_oqish #grammar #speaking #english",
            "#matematika #fizika #kimyo #biologiya #tarix",
            "#sertifikat #diplom #bilim #rivojlanish #career",
        ]
    },
    "oziq": {
        "nomi": "🍽️ 𝗢𝘃𝗾𝗮𝘁 𝘃𝗮 𝗥𝗲𝘀𝘁𝗼𝗿𝗮𝗻",
        "taglar": [
            "#ovqat #taom #restoran #cafe #yemak",
            "#milliy_taomlar #oshpaz #recipe #retsept #cooking",
            "#delivery #yetkazib_berish #pizza #burger #sushi",
            "#nonushta #tushlik #kechki_ovqat #ziyofat #tort",
            "#vegan #diet #sog_lom_ovqat #kaloriya #nutrition",
        ]
    },
    "texnologiya": {
        "nomi": "💻 𝗧𝗲𝘅𝗻𝗼𝗹𝗼𝗴𝗶𝘆𝗮",
        "taglar": [
            "#texnologiya #tech #innovation #gadget #smartphone",
            "#AI #suniy_intellekt #machinelearning #robot #future",
            "#cybersecurity #xavfsizlik #hacking #privacy #data",
            "#mobile #android #ios #app #ilovalar",
            "#cloud #server #hosting #database #software",
        ]
    },
    "soglik": {
        "nomi": "❤️ 𝗦𝗼𝗴'𝗹𝗶𝗾 𝘃𝗮 𝗙𝗶𝘁𝗻𝗲𝘀",
        "taglar": [
            "#soglik #salomatlik #tibbiyot #doktor #klinika",
            "#fitness #gym #workout #muskul #crossfit",
            "#yoga #meditatsiya #mindfulness #stresssiz #ruh",
            "#parhez #diet #ozayish #vaznni_kamaytirish #slim",
            "#vitamin #supplement #sog_lom_hayot #wellbeing #detox",
        ]
    },
    "kino": {
        "nomi": "🎬 𝗞𝗼'𝗻𝗴𝗶𝗹𝗼𝗰𝗵𝗮𝗿",
        "taglar": [
            "#kino #film #serial #anime #netflix",
            "#musiqa #qoshiq #artist #concert #live",
            "#gaming #oyin #playstation #xbox #mobile_game",
            "#komediya #hazil #meme #trend #viral",
            "#uzbekfilm #ozbekmusiqasi #milliy #madaniyat #sanaat",
        ]
    },
    "uy": {
        "nomi": "🏠 𝗨𝘆 𝘃𝗮 𝗗𝗶𝘇𝗮𝘆𝗻",
        "taglar": [
            "#uy #kvartira #interer #dizayn #dekor",
            "#remont #qurilish #mebel #mebeldesign #homedesign",
            "#bog #gul #ochilar #tabiat #green",
            "#realestate #kochirilmas_mulk #sotiladi #ijaraga #yangiuy",
            "#handmade #qolbola #crafts #DIY #homemade",
        ]
    },
    "moda": {
        "nomi": "👗 𝗠𝗼𝗱𝗮 𝘃𝗮 𝗚𝗼'𝘇𝗮𝗹𝗹𝗶𝗸",
        "taglar": [
            "#moda #fashion #style #trend #ootd",
            "#gozellik #makeup #beauty #skincare #parfum",
            "#kiyim #aksesuar #sumka #poyabzal #bijuteriya",
            "#milliy_kiyim #atlas #ipak #uzbekmoda #handmade",
            "#fitness_look #sport_kiyim #casual #formal #classic",
        ]
    },
    "uzbekiston": {
        "nomi": "🇺🇿 𝗢'𝘇𝗯𝗲𝗸𝗶𝘀𝘁𝗼𝗻",
        "taglar": [
            "#uzbekiston #toshkent #samarqand #buxoro #namangan",
            "#uzbek #ozbek #milliy #vatandosh #mening_yurtim",
            "#visituzbekistan #uzbektourism #silk_road #tariximiz #madaniyat",
            "#uzbekfood #osh #somsa #shashlik #lagmon",
            "#uzb #uzbek_blogger #ozbek_content #uzbekmedia #tashkent",
        ]
    }
}

def custom_hashtags_yukla():
    return json_yukla(CUSTOM_HASHTAGS_FILE, {})

def custom_hashtags_saqlash(data):
    json_saqlash(CUSTOM_HASHTAGS_FILE, data)

def barcha_hashtags():
    merged = dict(HASHTAGS)
    merged.update(custom_hashtags_yukla())
    return merged

# ═══════════════════════════════════════════════════════════════
# 🎯  INSTAGRAM
# ═══════════════════════════════════════════════════════════════

INSTAGRAM_REGEX = re.compile(
    r'(https?://)?(www\.)?instagram\.com/'
    r'(p|reel|reels|tv|stories)/[A-Za-z0-9_\-]+/?'
)

def instagram_url_mi(matn):
    return bool(INSTAGRAM_REGEX.search(matn))

def url_ajrat(matn):
    n = INSTAGRAM_REGEX.search(matn)
    return n.group(0) if n else None

def instagram_video_yukla(url):
    tmp_dir   = tempfile.mkdtemp()
    fayl_nomi = os.path.join(tmp_dir, "instagram_%(id)s.%(ext)s")
    ydl_opts  = {
        "outtmpl":     fayl_nomi,
        "quiet":       True,
        "no_warnings": True,
        "format":      "best[ext=mp4]/best",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info        = ydl.extract_info(url, download=True)
            yuklab_fayl = ydl.prepare_filename(info)
            if os.path.exists(yuklab_fayl):
                yuklab_olish_hisob()
                return yuklab_fayl, "video"
            for f in os.listdir(tmp_dir):
                to_liq = os.path.join(tmp_dir, f)
                if os.path.isfile(to_liq):
                    yuklab_olish_hisob()
                    return to_liq, "video"
        return None, "❌ Fayl topilmadi."
    except yt_dlp.utils.DownloadError as e:
        xato = str(e)
        if "Private" in xato or "login" in xato.lower():
            return None, "🔒 Bu post yopiq yoki login talab qiladi."
        if "not found" in xato.lower() or "404" in xato:
            return None, "❌ Post topilmadi."
        return None, f"⚠️ Yuklab bo'lmadi: {xato[:200]}"
    except Exception as e:
        log.error(f"Video yuklab olish xatosi: {e}")
        return None, f"⚠️ Xatolik: {str(e)[:200]}"

def faylni_tozala(yol):
    try:
        if yol and os.path.exists(yol):
            os.remove(yol)
            parent = os.path.dirname(yol)
            if os.path.isdir(parent):
                os.rmdir(parent)
    except:
        pass

# ═══════════════════════════════════════════════════════════════
# 🔔  OBUNA
# ═══════════════════════════════════════════════════════════════

def obuna_tekshir(user_id):
    if admin_mi(user_id):
        return True
    try:
        obuna = bot.get_chat_member(KANAL, user_id)
        return obuna.status in ["member", "administrator", "creator"]
    except:
        return False

def obuna_xabari(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Kanalga obuna bo'lish", url=f"https://t.me/{KANAL[1:]}"))
    markup.add(types.InlineKeyboardButton("🔄 Tekshirish", callback_data="obuna_tekshir"))
    bot.send_message(
        chat_id,
        "🚫 *Botdan foydalanish uchun avval kanalga obuna bo'ling:*\n\n"
        f"👉 {KANAL}\n\nObuna bo'lgach «Tekshirish» tugmasini bosing.",
        reply_markup=markup
    )

# ═══════════════════════════════════════════════════════════════
# ⌨️  KLAVIATURALAR
# ═══════════════════════════════════════════════════════════════

def asosiy_menu(user_id=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📥 Video Yuklab olish"),
        types.KeyboardButton("🏷 Hashtaglar")
    )
    markup.add(
        types.KeyboardButton("⭐ Sevimlilar"),
        types.KeyboardButton("ℹ️ Bot haqida")
    )
    if user_id and admin_mi(user_id):
        markup.add(types.KeyboardButton("🔐 Admin Panel"))
    return markup

def video_bolim_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⬅️ Orqaga"))
    return markup

def hashtag_bolim_menu():
    barcha = barcha_hashtags()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(*[types.KeyboardButton(v["nomi"]) for v in barcha.values()])
    markup.add(types.KeyboardButton("⬅️ Orqaga"))
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📢 Xabar yuborish"),
        types.KeyboardButton("📊 Statistika")
    )
    markup.add(
        types.KeyboardButton("🚫 Foydalanuvchi blokla"),
        types.KeyboardButton("✅ Blokdan chiqar")
    )
    markup.add(
        types.KeyboardButton("➕ Yangi kategoriya"),
        types.KeyboardButton("🗑 Kategoriya o'chir")
    )
    markup.add(
        types.KeyboardButton("🔍 Foydalanuvchi qidir"),
        types.KeyboardButton("📝 Ro'yxat yuklab olish")
    )
    markup.add(
        types.KeyboardButton("💬 Shaxsiy xabar"),
        types.KeyboardButton("⏰ Rejalashtirilgan xabar")
    )
    markup.add(
        types.KeyboardButton("👮 Admin qo'shish"),
        types.KeyboardButton("❌ Admin o'chirish")
    )
    markup.add(
        types.KeyboardButton("👥 Admin ro'yxati"),
        types.KeyboardButton("💾 Backup olish")
    )
    markup.add(
        types.KeyboardButton("📣 Kanal xabari"),
        types.KeyboardButton("📋 Log faylni olish")
    )
    markup.add(
        types.KeyboardButton("📌 Botni to'xtatish"),
        types.KeyboardButton("🟢 Botni yoqish")
    )
    markup.add(
        types.KeyboardButton("👥 Foydalanuvchilar soni"),
        types.KeyboardButton("🔙 Oddiy menyu")
    )
    return markup

def hashtaglar_inline(kategoriya_kodi, user_id=None):
    barcha = barcha_hashtags()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, guruh in enumerate(barcha[kategoriya_kodi]["taglar"]):
        birinchi = guruh.split()[0]
        markup.add(types.InlineKeyboardButton(
            f"📋 {birinchi} … ({len(guruh.split())} ta)",
            callback_data=f"tag_{kategoriya_kodi}_{i}"
        ))
    markup.add(types.InlineKeyboardButton("⭐ Sevimlilarga qo'shish", callback_data=f"fav_menu_{kategoriya_kodi}"))
    return markup

def kategoriya_kodini_top(nomi):
    for kod, v in barcha_hashtags().items():
        if v["nomi"] == nomi:
            return kod
    return None

# ═══════════════════════════════════════════════════════════════
# 🗂️  HOLATLAR
# ═══════════════════════════════════════════════════════════════

user_states = {}
admin_temp  = {}

# ═══════════════════════════════════════════════════════════════
# 🚀  /start
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    foydalanuvchi_qoshish(message.from_user)
    faoliyat_yangilash(uid)

    if bloklangan_mi(uid):
        bot.send_message(message.chat.id, "🚫 Siz botdan bloklangansiz.")
        return

    if BOT_TOXTATILGAN and not admin_mi(uid):
        bot.send_message(message.chat.id, TEXNIK_XABAR)
        return

    if not obuna_tekshir(uid):
        obuna_xabari(message.chat.id)
        return

    user_states[uid] = None
    bot.send_message(
        message.chat.id,
        "👋 *Salom! Men* 𝗛𝗮𝘀𝗵𝘁𝗮𝗴 𝗕𝗼𝘁 *man!*\n\n"
        "📥 *Video Yuklab olish* — Instagram Reel/Post/Stories\n"
        "🏷 *Hashtaglar* — 500+ tayyor hashtag\n"
        "⭐ *Sevimlilar* — saqlangan hashtaglaringiz\n\n"
        "👇 Bo'lim tanlang:",
        parse_mode="Markdown",
        reply_markup=asosiy_menu(uid)
    )

# ═══════════════════════════════════════════════════════════════
# 🔐  /admin
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    uid = message.from_user.id
    if not admin_mi(uid):
        bot.send_message(message.chat.id, "❌ Siz admin emassiz.")
        log.warning(f"Admin paneliga ruxsatsiz urinish: {uid}")
        return
    user_states[uid] = "admin"
    users = users_yukla()
    bot.send_message(
        message.chat.id,
        f"🔐 *𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹*\n\n"
        f"👥 Foydalanuvchilar: *{len(users)}* ta\n"
        f"🤖 Bot: {'🔴 To\\'xtatilgan' if BOT_TOXTATILGAN else '🟢 Ishlayapti'}\n\n"
        "Amal tanlang:",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )

@bot.message_handler(commands=['help'])
def help_cmd(message):
    if not obuna_tekshir(message.from_user.id):
        obuna_xabari(message.chat.id)
        return
    bot.send_message(
        message.chat.id,
        "📖 *𝗬𝗼𝗿𝗱𝗮𝗺*\n\n"
        "/start — Boshlanish\n"
        "/help — Yordam\n"
        "/mystats — Shaxsiy statistika\n"
        "/admin — Admin panel (faqat adminlar)\n",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['mystats'])
def mystats_cmd(message):
    uid      = message.from_user.id
    favs     = favorites_yukla()
    activity = activity_yukla()
    users    = users_yukla()
    u        = users.get(str(uid), {})
    fav_son  = len(favs.get(str(uid), []))
    oxirgi   = activity.get(str(uid), "—")

    bot.send_message(
        message.chat.id,
        f"📊 *Mening statistikam*\n\n"
        f"👤 Ism: {u.get('ism', '-')}\n"
        f"🆔 ID: `{uid}`\n"
        f"📅 Qo'shilgan: {u.get('qoshilgan', '-')}\n"
        f"⭐ Sevimli hashtaglar: {fav_son} ta\n"
        f"🕐 Oxirgi faollik: {oxirgi}",
        parse_mode="Markdown"
    )

# ═══════════════════════════════════════════════════════════════
# 💬  MATN HANDLER
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(content_types=['text'])
def matn_handler(message):
    global BOT_TOXTATILGAN

    uid   = message.from_user.id
    matn  = message.text.strip()
    holat = user_states.get(uid)

    foydalanuvchi_qoshish(message.from_user)
    faoliyat_yangilash(uid)

    if bloklangan_mi(uid) and not admin_mi(uid):
        bot.send_message(message.chat.id, "🚫 Siz botdan bloklangansiz.")
        return

    if BOT_TOXTATILGAN and not admin_mi(uid):
        bot.send_message(message.chat.id, TEXNIK_XABAR)
        return

    if spam_tekshir(uid):
        bot.send_message(message.chat.id, "⚠️ Juda tez xabar yuborayapsiz! 60 soniya kuting.")
        return

    if matn == "🔐 Admin Panel":
        if not admin_mi(uid):
            bot.send_message(message.chat.id, "❌ Ruxsat yo'q.")
            return
        user_states[uid] = "admin"
        bot.send_message(message.chat.id, "🔐 *Admin Panel*\n\nAmal tanlang:",
            parse_mode="Markdown", reply_markup=admin_menu())
        return

    if holat == "admin" and admin_mi(uid):

        if matn == "📢 Xabar yuborish":
            user_states[uid] = "broadcast"
            bot.send_message(message.chat.id,
                "✏️ Barcha foydalanuvchilarga yuboriladigan xabarni yozing:\n(Bekor: /bekor)")
            return

        if matn == "📊 Statistika":
            bot.send_message(message.chat.id, statistika_matn(), parse_mode="Markdown")
            return

        if matn == "🚫 Foydalanuvchi blokla":
            user_states[uid] = "blokla"
            bot.send_message(message.chat.id,
                "🚫 *Bloklash*\n\nFoydalanuvchi ID yuboring:\n_(Misol: 123456789)_\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "✅ Blokdan chiqar":
            blocked = blocked_yukla()
            if not blocked:
                bot.send_message(message.chat.id, "✅ Bloklangan foydalanuvchi yo'q.")
                return
            user_states[uid] = "blokdan_chiqar"
            royxat = "\n".join([f"• `{v['id']}` — {v['ism']} | {v['sabab']}" for v in blocked.values()])
            bot.send_message(message.chat.id,
                f"📋 *Bloklangan foydalanuvchilar:*\n\n{royxat}\n\nID yuboring:\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "➕ Yangi kategoriya":
            user_states[uid] = "yangi_kat_nom"
            admin_temp[uid]  = {}
            bot.send_message(message.chat.id,
                "➕ *Yangi Hashtag Kategoriya*\n\n"
                "1️⃣ Kategoriya nomini yozing:\n_(Misol: 🎨 Sanat va Dizayn)_\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "🗑 Kategoriya o'chir":
            custom = custom_hashtags_yukla()
            if not custom:
                bot.send_message(message.chat.id, "📭 O'chiriladigan maxsus kategoriya yo'q.")
                return
            user_states[uid] = "kat_ochir"
            royxat = "\n".join([f"• `{kod}` — {v['nomi']}" for kod, v in custom.items()])
            bot.send_message(message.chat.id,
                f"🗑 *Qaysi kategoriyani o'chirmoqchisiz?*\n\n{royxat}\n\n"
                "Kategoriya *kodini* yuboring (masalan: `sanaat`)\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "🔍 Foydalanuvchi qidir":
            user_states[uid] = "qidirish"
            bot.send_message(message.chat.id,
                "🔍 *Qidirish*\n\nFoydalanuvchi ID yoki @username yuboring:\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "📝 Ro'yxat yuklab olish":
            mazmun = users_txt_export()
            tmp    = tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                                  delete=False, encoding="utf-8")
            tmp.write(mazmun)
            tmp.close()
            with open(tmp.name, "rb") as f:
                bot.send_document(message.chat.id, f,
                    caption=f"📝 Foydalanuvchilar ro'yxati\n📅 {date.today()}",
                    visible_file_name="foydalanuvchilar.txt")
            os.unlink(tmp.name)
            return

        if matn == "💬 Shaxsiy xabar":
            user_states[uid] = "shaxsiy_id"
            bot.send_message(message.chat.id,
                "💬 *Shaxsiy Xabar*\n\nFoydalanuvchi ID yuboring:\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "⏰ Rejalashtirilgan xabar":
            user_states[uid] = "rejali_vaqt"
            bot.send_message(message.chat.id,
                "⏰ *Rejalashtirilgan Xabar*\n\n"
                "Yuborish vaqtini kiriting (24-soat format):\n"
                "_(Misol: 20:30)_\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "👮 Admin qo'shish":
            if not super_admin_mi(uid):
                bot.send_message(message.chat.id, "❌ Faqat super admin admin qo'sha oladi.")
                return
            user_states[uid] = "admin_qosh"
            bot.send_message(message.chat.id,
                "👮 *Yangi Admin*\n\nFoydalanuvchi ID yuboring:\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "❌ Admin o'chirish":
            if not super_admin_mi(uid):
                bot.send_message(message.chat.id, "❌ Faqat super admin admin o'chira oladi.")
                return
            admins = admins_yukla()
            if not admins:
                bot.send_message(message.chat.id, "📭 Qo'shilgan admin yo'q.")
                return
            user_states[uid] = "admin_ochir"
            royxat = "\n".join([f"• `{v['id']}` — {v.get('ism','-')}" for v in admins.values()])
            bot.send_message(message.chat.id,
                f"❌ *Adminlar:*\n\n{royxat}\n\nO'chirmoqchi bo'lgan admin ID yuboring:\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "👥 Admin ro'yxati":
            qatorlar = admin_royxat()
            if not qatorlar:
                asosiy = "\n".join([f"• `{a}` — Super Admin" for a in ADMIN_IDS])
                bot.send_message(message.chat.id,
                    f"👮 *Adminlar:*\n\n{asosiy}\n\n_(Qo'shilgan admin yo'q)_",
                    parse_mode="Markdown")
            else:
                asosiy    = "\n".join([f"• `{a}` — ⭐ Super Admin" for a in ADMIN_IDS])
                qoshilgan = "\n".join(qatorlar)
                bot.send_message(message.chat.id,
                    f"👮 *Adminlar:*\n\n*Super Adminlar:*\n{asosiy}\n\n*Adminlar:*\n{qoshilgan}",
                    parse_mode="Markdown")
            return

        if matn == "💾 Backup olish":
            bot.send_message(message.chat.id, "⏳ Backup yaratilmoqda…")
            try:
                zip_nomi = backup_yaratish()
                with open(zip_nomi, "rb") as f:
                    bot.send_document(message.chat.id, f,
                        caption=f"💾 Backup — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        visible_file_name=f"backup_{date.today()}.zip")
                os.unlink(zip_nomi)
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Xatolik: {e}")
            return

        if matn == "📣 Kanal xabari":
            user_states[uid] = "kanal_xabar"
            bot.send_message(message.chat.id,
                "📣 *Kanal Xabari*\n\n"
                f"Kanal: {KANAL}\n\n"
                "Kanalga yuboriladigan xabarni yozing:\n\nBekor: /bekor",
                parse_mode="Markdown")
            return

        if matn == "📋 Log faylni olish":
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "rb") as f:
                    bot.send_document(message.chat.id, f,
                        caption=f"📋 Bot loglari — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        visible_file_name="bot.log")
            else:
                bot.send_message(message.chat.id, "📭 Log fayl topilmadi.")
            return

        if matn == "📌 Botni to'xtatish":
            BOT_TOXTATILGAN = True
            bot.send_message(message.chat.id,
                "🔴 *Bot to'xtatildi!*\n\n"
                "Foydalanuvchilar texnik xabar ko'radi.\n"
                "Qayta yoqish uchun '🟢 Botni yoqish' bosing.",
                parse_mode="Markdown", reply_markup=admin_menu())
            log.info(f"Bot to'xtatildi. Admin: {uid}")
            return

        if matn == "🟢 Botni yoqish":
            BOT_TOXTATILGAN = False
            bot.send_message(message.chat.id,
                "🟢 *Bot qayta yoqildi!*\n\nFoydalanuvchilar yana foydalana oladi.",
                parse_mode="Markdown", reply_markup=admin_menu())
            log.info(f"Bot yoqildi. Admin: {uid}")
            return

        if matn == "👥 Foydalanuvchilar soni":
            users   = users_yukla()
            blocked = blocked_yukla()
            bot.send_message(message.chat.id,
                f"👥 Jami: *{len(users)}* ta\n"
                f"✅ Faol: *{len(users) - len(blocked)}* ta\n"
                f"🚫 Bloklangan: *{len(blocked)}* ta",
                parse_mode="Markdown")
            return

        if matn == "🔙 Oddiy menyu":
            user_states[uid] = None
            bot.send_message(message.chat.id, "✅ Asosiy menyuga qaytdingiz.",
                reply_markup=asosiy_menu(uid))
            return

    if holat == "broadcast" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor qilindi.", reply_markup=admin_menu())
            return
        userlar   = barcha_userlar()
        yuborildi = 0
        xato      = 0
        prog      = bot.send_message(message.chat.id, f"⏳ Yuborilmoqda… 0/{len(userlar)}")
        for i, user_id in enumerate(userlar):
            try:
                bot.send_message(user_id, f"📢 *Yangilik:*\n\n{matn}", parse_mode="Markdown")
                yuborildi += 1
            except:
                xato += 1
            if (i + 1) % 20 == 0:
                try:
                    bot.edit_message_text(f"⏳ Yuborilmoqda… {i+1}/{len(userlar)}",
                        message.chat.id, prog.message_id)
                except:
                    pass
        bot.edit_message_text(
            f"✅ *Yuborildi!*\n\n✔️ Muvaffaqiyatli: {yuborildi}\n❌ Xato: {xato}\n📊 Jami: {len(userlar)}",
            message.chat.id, prog.message_id, parse_mode="Markdown")
        user_states[uid] = "admin"
        bot.send_message(message.chat.id, "Admin panel:", reply_markup=admin_menu())
        log.info(f"Broadcast: {yuborildi}/{len(userlar)} — Admin: {uid}")
        return

    if holat == "blokla" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        try:
            blok_id = int(matn.strip())
            if admin_mi(blok_id):
                bot.send_message(message.chat.id, "❌ Adminni bloklab bo'lmaydi!")
                return
            foydalanuvchi_blokla(blok_id)
            bot.send_message(message.chat.id,
                f"🚫 Foydalanuvchi *{blok_id}* bloklandi.",
                parse_mode="Markdown", reply_markup=admin_menu())
            try:
                bot.send_message(blok_id, "🚫 Siz botdan bloklangansiz.")
            except:
                pass
        except ValueError:
            bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting.")
            return
        user_states[uid] = "admin"
        return

    if holat == "blokdan_chiqar" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        try:
            blok_id = int(matn.strip())
            if foydalanuvchi_blokdan_chiqar(blok_id):
                bot.send_message(message.chat.id,
                    f"✅ *{blok_id}* blokdan chiqarildi.",
                    parse_mode="Markdown", reply_markup=admin_menu())
                try:
                    bot.send_message(blok_id, "✅ Siz blokdan chiqarildingiz! /start bosing.")
                except:
                    pass
            else:
                bot.send_message(message.chat.id, "⚠️ Bu ID bloklangan ro'yxatda yo'q.")
        except ValueError:
            bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting.")
            return
        user_states[uid] = "admin"
        return

    if holat == "admin_qosh" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        try:
            yangi_admin_id = int(matn.strip())
            users   = users_yukla()
            u_info  = users.get(str(yangi_admin_id), {})
            admin_qosh(yangi_admin_id, u_info.get("ism",""), u_info.get("username",""))
            bot.send_message(message.chat.id,
                f"✅ *{yangi_admin_id}* endi admin.",
                parse_mode="Markdown", reply_markup=admin_menu())
            try:
                bot.send_message(yangi_admin_id,
                    "🎉 *Tabriklaymiz!* Siz bot admini sifatida tayinlandingiz!\n/admin yuboring.",
                    parse_mode="Markdown")
            except:
                pass
        except ValueError:
            bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting.")
            return
        user_states[uid] = "admin"
        return

    if holat == "admin_ochir" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        try:
            ochir_id = int(matn.strip())
            if ochir_id in ADMIN_IDS:
                bot.send_message(message.chat.id, "❌ Super adminni o'chirib bo'lmaydi!")
                return
            if admin_ochir(ochir_id):
                bot.send_message(message.chat.id,
                    f"✅ *{ochir_id}* admin ro'yxatidan chiqarildi.",
                    parse_mode="Markdown", reply_markup=admin_menu())
                try:
                    bot.send_message(ochir_id, "ℹ️ Sizning admin huquqingiz bekor qilindi.")
                except:
                    pass
            else:
                bot.send_message(message.chat.id, "⚠️ Bu ID admin ro'yxatida yo'q.")
        except ValueError:
            bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting.")
            return
        user_states[uid] = "admin"
        return

    if holat == "yangi_kat_nom" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        admin_temp[uid]["nomi"] = matn
        user_states[uid] = "yangi_kat_tag"
        bot.send_message(message.chat.id,
            f"✅ Nom: *{matn}*\n\n"
            "2️⃣ Hashtaglarni yuboring (har qatorga bir guruh):\n\n"
            "_Misol:_\n`#sanaat #rasm #chizish #eskiz`\n`#akvarell #grafika #art`\n\nBekor: /bekor",
            parse_mode="Markdown")
        return

    if holat == "yangi_kat_tag" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        qatorlar = [q.strip() for q in matn.strip().splitlines() if q.strip()]
        if not qatorlar:
            bot.send_message(message.chat.id, "⚠️ Kamida bitta guruh kiriting.")
            return
        nom    = admin_temp[uid].get("nomi", "Yangi kategoriya")
        kod    = re.sub(r'[^a-zA-Z0-9]', '_', nom.lower())[:20].strip('_') or f"cat_{len(custom_hashtags_yukla())+1}"
        custom = custom_hashtags_yukla()
        custom[kod] = {"nomi": nom, "taglar": qatorlar}
        custom_hashtags_saqlash(custom)
        bot.send_message(message.chat.id,
            f"✅ *Kategoriya qo'shildi!*\n\n📂 Nom: *{nom}*\n📋 Guruhlar: *{len(qatorlar)}* ta",
            parse_mode="Markdown", reply_markup=admin_menu())
        user_states[uid] = "admin"
        admin_temp.pop(uid, None)
        return

    if holat == "kat_ochir" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        custom = custom_hashtags_yukla()
        kod    = matn.strip()
        if kod in custom:
            nom = custom[kod]["nomi"]
            del custom[kod]
            custom_hashtags_saqlash(custom)
            bot.send_message(message.chat.id,
                f"🗑 *{nom}* kategoriyasi o'chirildi.",
                parse_mode="Markdown", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id,
                f"⚠️ `{kod}` kodi topilmadi.", parse_mode="Markdown")
            return
        user_states[uid] = "admin"
        return

    if holat == "qidirish" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        natija = foydalanuvchi_qidir(matn)
        if natija:
            blocked  = blocked_yukla()
            activity = activity_yukla()
            favs     = favorites_yukla()
            holat_b  = "🚫 Bloklangan" if str(natija['id']) in blocked else "✅ Faol"
            oxirgi   = activity.get(str(natija['id']), "—")
            fav_son  = len(favs.get(str(natija['id']), []))
            bot.send_message(message.chat.id,
                f"🔍 *Topildi:*\n\n"
                f"🆔 ID: `{natija['id']}`\n"
                f"👤 Ism: {natija.get('ism', '-')}\n"
                f"📛 Username: @{natija.get('username', '-')}\n"
                f"📅 Qo'shilgan: {natija.get('qoshilgan', '-')}\n"
                f"🕐 Oxirgi faollik: {oxirgi}\n"
                f"⭐ Sevimlilar: {fav_son} ta\n"
                f"📌 Holat: {holat_b}",
                parse_mode="Markdown", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "❌ Foydalanuvchi topilmadi.")
        user_states[uid] = "admin"
        return

    if holat == "shaxsiy_id" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        try:
            xabar_id = int(matn.strip())
            admin_temp[uid] = {"shaxsiy_id": xabar_id}
            user_states[uid] = "shaxsiy_matn"
            bot.send_message(message.chat.id,
                f"✅ ID: *{xabar_id}*\n\nXabarni yozing:\n\nBekor: /bekor",
                parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting.")
        return

    if holat == "shaxsiy_matn" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        xabar_id = admin_temp.get(uid, {}).get("shaxsiy_id")
        try:
            bot.send_message(xabar_id, f"💬 *Admin xabari:*\n\n{matn}", parse_mode="Markdown")
            bot.send_message(message.chat.id,
                f"✅ Xabar *{xabar_id}* ga yuborildi.",
                parse_mode="Markdown", reply_markup=admin_menu())
        except Exception as e:
            bot.send_message(message.chat.id,
                f"❌ Yuborib bo'lmadi: {str(e)[:100]}", reply_markup=admin_menu())
        user_states[uid] = "admin"
        admin_temp.pop(uid, None)
        return

    if holat == "kanal_xabar" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        try:
            bot.send_message(KANAL, matn, parse_mode="Markdown")
            bot.send_message(message.chat.id,
                f"✅ Kanal ({KANAL}) ga xabar yuborildi!",
                reply_markup=admin_menu())
        except Exception as e:
            bot.send_message(message.chat.id,
                f"❌ Yuborib bo'lmadi: {str(e)[:150]}\n\nBot kanalda admin bo'lishi kerak.",
                reply_markup=admin_menu())
        user_states[uid] = "admin"
        return

    if holat == "rejali_vaqt" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        if not re.match(r'^\d{2}:\d{2}$', matn.strip()):
            bot.send_message(message.chat.id,
                "⚠️ Noto'g'ri format. HH:MM kiriting. Masalan: `20:30`", parse_mode="Markdown")
            return
        admin_temp[uid] = {"rejali_vaqt": matn.strip()}
        user_states[uid] = "rejali_matn"
        bot.send_message(message.chat.id,
            f"✅ Vaqt: *{matn}*\n\nXabar matnini yozing:\n\nBekor: /bekor",
            parse_mode="Markdown")
        return

    if holat == "rejali_matn" and admin_mi(uid):
        if matn == "/bekor":
            user_states[uid] = "admin"
            bot.send_message(message.chat.id, "❌ Bekor.", reply_markup=admin_menu())
            return
        vaqt = admin_temp.get(uid, {}).get("rejali_vaqt", "20:00")
        rejalashtirilgan_xabar_yuborish(vaqt, matn)
        bot.send_message(message.chat.id,
            f"⏰ *Rejalashtirildi!*\n\n"
            f"🕐 Vaqt: *{vaqt}*\n"
            f"📝 Xabar: {matn[:100]}{'...' if len(matn) > 100 else ''}\n\n"
            "Xabar belgilangan vaqtda avtomatik yuboriladi.",
            parse_mode="Markdown", reply_markup=admin_menu())
        user_states[uid] = "admin"
        admin_temp.pop(uid, None)
        return

    if not obuna_tekshir(uid):
        obuna_xabari(message.chat.id)
        return

    if matn == "⬅️ Orqaga":
        user_states[uid] = None
        bot.send_message(message.chat.id, "🏠 𝗔𝘀𝗼𝘀𝗶𝘆 𝗺𝗲𝗻𝘆𝘂:", reply_markup=asosiy_menu(uid))
        return

    if holat is None:
        if matn == "📥 Video Yuklab olish":
            user_states[uid] = "video"
            bot.send_message(message.chat.id,
                "📥 *𝗩𝗶𝗱𝗲𝗼 𝗬𝘂𝗸𝗹𝗮𝗯 𝗢𝗹𝗶𝘀𝗵*\n\n"
                "🎬 Reels  🖼 Post  📖 Stories\n\n"
                "Instagram havolasini yuboring:\n"
                "`https://www.instagram.com/reel/ABC123/`\n\n"
                "⚠️ Yopiq postlar yuklanmaydi.",
                parse_mode="Markdown", reply_markup=video_bolim_menu())
            return

        if matn == "🏷 Hashtaglar":
            user_states[uid] = "hashtag"
            bot.send_message(message.chat.id,
                "🏷 *𝗛𝗮𝘀𝗵𝘁𝗮𝗴 𝗕𝗼'𝗹𝗶𝗺𝗶*\n\nKategoriya tanlang:",
                parse_mode="Markdown", reply_markup=hashtag_bolim_menu())
            return

        if matn == "⭐ Sevimlilar":
            user_states[uid] = "sevimlilar"
            items = sevimlilar_royxat(uid)
            if not items:
                bot.send_message(message.chat.id,
                    "⭐ *Sevimlilar bo'sh*\n\nHashtag ko'rganingizda ⭐ tugmasi orqali saqlang.",
                    parse_mode="Markdown", reply_markup=asosiy_menu(uid))
            else:
                markup = types.InlineKeyboardMarkup(row_width=1)
                for item in items:
                    birinchi = item["taglar"].split()[0]
                    markup.add(types.InlineKeyboardButton(
                        f"📋 {birinchi}…",
                        callback_data=f"sev_ko_{item['kalit']}"
                    ))
                    markup.add(types.InlineKeyboardButton(
                        f"🗑 O'chirish",
                        callback_data=f"sev_del_{item['kalit']}"
                    ))
                bot.send_message(message.chat.id,
                    f"⭐ *Sevimlilaringiz* ({len(items)} ta):",
                    parse_mode="Markdown", reply_markup=markup)
            user_states[uid] = None
            return

        if matn == "ℹ️ Bot haqida":
            users  = users_yukla()
            barcha = barcha_hashtags()
            stats  = stats_yukla()
            bot.send_message(message.chat.id,
                "🤖 *𝗛𝗮𝘀𝗵𝘁𝗮𝗴 𝗕𝗼𝘁*\n\n"
                f"👥 Foydalanuvchilar: {len(users)} ta\n"
                f"📂 {len(barcha)} ta kategoriya\n"
                f"📥 Jami yuklamalar: {stats.get('yuklamalar', 0)} ta\n"
                f"🏷 Hashtag so'rovlar: {stats.get('hashtag_sorov', 0)} ta\n"
                "🇺🇿 O'zbek tilida  |  ✅ Bepul\n\n"
                "/mystats — shaxsiy statistika",
                parse_mode="Markdown")
            return

        bot.send_message(message.chat.id, "👇 Bo'lim tanlang:", reply_markup=asosiy_menu(uid))
        return

    if holat == "video":
        if instagram_url_mi(matn):
            url    = url_ajrat(matn)
            kutish = bot.send_message(message.chat.id, "⏳ Video yuklanmoqda…")
            fayl_yoli, tur = instagram_video_yukla(url)
            try:
                bot.delete_message(message.chat.id, kutish.message_id)
            except:
                pass
            if fayl_yoli:
                try:
                    with open(fayl_yoli, "rb") as f:
                        bot.send_video(message.chat.id, f,
                            caption="✅ Mana sizning videongiz!\n\n📥 @instaheshtegbot",
                            supports_streaming=True)
                except:
                    try:
                        with open(fayl_yoli, "rb") as f:
                            bot.send_document(message.chat.id, f,
                                caption="✅ Mana sizning faylingiz!\n\n📥 @instaheshtegbot")
                    except Exception as e:
                        bot.send_message(message.chat.id, f"⚠️ Xatolik: {str(e)[:200]}")
                finally:
                    faylni_tozala(fayl_yoli)
            else:
                bot.send_message(message.chat.id, tur)
        else:
            bot.send_message(message.chat.id,
                "⚠️ Instagram havolasi emas.\n\n"
                "Misol: `https://www.instagram.com/reel/ABC123/`",
                parse_mode="Markdown")
        return

    if holat == "hashtag":
        kod = kategoriya_kodini_top(matn)
        if kod:
            hashtag_sorov_hisob()
            bot.send_message(message.chat.id,
                f"{barcha_hashtags()[kod]['nomi']}\n\n📋 Qaysi guruhni olmoqchisiz?",
                reply_markup=hashtaglar_inline(kod, uid))
        else:
            bot.send_message(message.chat.id, "👇 Kategoriya tanlang:", reply_markup=hashtag_bolim_menu())
        return

# ═══════════════════════════════════════════════════════════════
# 🔘  INLINE TUGMALAR
# ═══════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid  = call.from_user.id
    data = call.data

    if data == "obuna_tekshir":
        if obuna_tekshir(uid):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            user_states[uid] = None
            bot.send_message(call.message.chat.id,
                "✅ *Rahmat! Obuna bo'ldingiz!*\n\n👇 Bo'lim tanlang:",
                parse_mode="Markdown", reply_markup=asosiy_menu(uid))
        else:
            bot.answer_callback_query(call.id, "❗ Hali obuna bo'lmadingiz!", show_alert=True)
        return

    if not obuna_tekshir(uid):
        bot.answer_callback_query(call.id, "❗ Avval kanalga obuna bo'ling!", show_alert=True)
        return

    if data.startswith("tag_"):
        qismlar = data.split("_", 2)
        kat_kod = qismlar[1]
        indeks  = int(qismlar[2])
        barcha  = barcha_hashtags()
        if kat_kod in barcha:
            taglar = barcha[kat_kod]["taglar"][indeks]
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "⭐ Sevimlilarga qo'shish",
                callback_data=f"fav_add_{kat_kod}_{indeks}"
            ))
            bot.send_message(call.message.chat.id,
                f"✅ *Nusxalab oling:*\n\n`{taglar}`",
                parse_mode="Markdown", reply_markup=markup)
        return

    if data.startswith("fav_menu_"):
        kat_kod = data[9:]
        barcha  = barcha_hashtags()
        if kat_kod not in barcha:
            bot.answer_callback_query(call.id, "❌ Kategoriya topilmadi", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, guruh in enumerate(barcha[kat_kod]["taglar"]):
            birinchi = guruh.split()[0]
            markup.add(types.InlineKeyboardButton(
                f"⭐ {birinchi}…",
                callback_data=f"fav_add_{kat_kod}_{i}"
            ))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "⭐ Qaysi guruhni sevimlilarga qo'shmoqchisiz?",
            reply_markup=markup)
        return

    if data.startswith("fav_add_"):
        qismlar = data[8:].split("_", 1)
        kat_kod = qismlar[0]
        indeks  = int(qismlar[1])
        if sevimli_qosh(uid, kat_kod, indeks):
            bot.answer_callback_query(call.id, "⭐ Sevimlilarga qo'shildi!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "ℹ️ Allaqachon sevimlilar ro'yxatida!", show_alert=True)
        return

    if data.startswith("sev_ko_"):
        kalit   = data[7:]
        qismlar = kalit.split("_", 1)
        kat_kod = qismlar[0]
        indeks  = int(qismlar[1])
        barcha  = barcha_hashtags()
        if kat_kod in barcha and indeks < len(barcha[kat_kod]["taglar"]):
            taglar = barcha[kat_kod]["taglar"][indeks]
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id,
                f"✅ *Nusxalab oling:*\n\n`{taglar}`",
                parse_mode="Markdown")
        return

    if data.startswith("sev_del_"):
        kalit = data[8:]
        if sevimli_ochir(uid, kalit):
            bot.answer_callback_query(call.id, "🗑 O'chirildi!", show_alert=True)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            items = sevimlilar_royxat(uid)
            if items:
                markup = types.InlineKeyboardMarkup(row_width=1)
                for item in items:
                    birinchi = item["taglar"].split()[0]
                    markup.add(types.InlineKeyboardButton(
                        f"📋 {birinchi}…", callback_data=f"sev_ko_{item['kalit']}"
                    ))
                    markup.add(types.InlineKeyboardButton(
                        "🗑 O'chirish", callback_data=f"sev_del_{item['kalit']}"
                    ))
                bot.send_message(call.message.chat.id,
                    f"⭐ *Sevimlilaringiz* ({len(items)} ta):",
                    parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id,
                    "⭐ Sevimlilar bo'sh.", reply_markup=asosiy_menu(uid))
        else:
            bot.answer_callback_query(call.id, "❌ Topilmadi", show_alert=True)
        return

# ═══════════════════════════════════════════════════════════════
# 🚀  ISHGA TUSHIRISH
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t = threading.Thread(target=schedule_runner, daemon=True)
    t.start()

    log.info("=" * 60)
    log.info("🤖 Hashtag Bot ishga tushdi")
    log.info(f"Admin IDs: {ADMIN_IDS}")
    log.info(f"Kanal: {KANAL}")
    log.info("=" * 60)

    print("🤖 𝗛𝗮𝘀𝗵𝘁𝗮𝗴 𝗕𝗼𝘁 ishga tushdi…")
    print(f"Admin IDs: {ADMIN_IDS}")
    print("To'xtatish uchun Ctrl+C bosing")

    bot.infinity_polling()
