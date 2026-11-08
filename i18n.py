"""Ko'p tillilik (uz / ru / en) va foydalanuvchi tilini saqlash."""
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_LANG = "uz"
LANG_NAMES = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "start": (
            "👋 Salom, <b>{name}</b>!\n\n"
            "Men audio va musiqa fayllarini tahrirlovchi botman. Menga <b>MP3, M4A, OGG, WAV</b> "
            "fayl yoki <b>ovozli xabar</b> yuboring, so'ng quyidagilarni qila olaman:\n\n"
            "✂️ <b>Qirqish</b> — audioning kerakli qismini kesib olish\n"
            "🔊 <b>Ovoz balandligi</b> — ovozni kuchaytirish yoki pasaytirish\n"
            "🏷 <b>Nom / Artist</b> — ID3 teglarni o'zgartirish\n"
            "📉 <b>Hajm / Bitrate</b> — fayl hajmini kichraytirish\n"
            "🖼 <b>Muqova</b> — audioga rasm qo'yish\n\n"
            "🌐 Tilni o'zgartirish: /language\n\n"
            "Boshlash uchun audio yuboring 🎧"
        ),
        "btn_trim": "✂️ Qirqish (Trim)",
        "btn_volume": "🔊 Ovoz balandligi",
        "btn_tags": "🏷 Nom / Artist (ID3)",
        "btn_bitrate": "📉 Hajm / Bitrate",
        "btn_cover": "🖼 Muqova (rasm)",
        "btn_lang": "🌐 Til",
        "btn_back": "⬅️ Orqaga",
        "btn_cancel": "❌ Bekor qilish",
        "send_audio_first": "Avval audio yuboring 🎧",
        "audio_received": "🎧 Audio qabul qilindi. Nima qilamiz?",
        "processing": "⏳ Ishlov berilmoqda…",
        "generic_error": "❌ Xatolik yuz berdi. Boshqa fayl bilan urinib ko'ring.",
        "cancelled_msg": "Bekor qilindi. Audio yuboring yoki tugmalardan foydalaning.",
        "cancelled_cb": "Bekor qilindi",
        "wrong_file": "⚠️ Iltimos, audio fayl yuboring (MP3, M4A, OGG, WAV) yoki ovozli xabar.",
        "file_too_big": "⚠️ Fayl juda katta. Maksimal hajm — 20 MB.",
        "cover_prompt": "🖼 Muqova qilmoqchi bo'lgan <b>rasmni</b> yuboring (oddiy rasm yoki fayl sifatida).",
        "cover_not_image": "⚠️ Iltimos, rasm yuboring (JPG, PNG).",
        "cover_too_big": "⚠️ Rasm juda katta (maksimal 20 MB).",
        "cover_need_image": "🖼 Iltimos, rasm yuboring yoki ❌ Bekor qilish tugmasini bosing.",
        "trim_prompt": (
            "✂️ Qaysi qismini qoldirish kerak? Vaqt oralig'ini yuboring:\n\n"
            "• <code>0:10-0:45</code> — 10-soniyadan 45-soniyagacha\n"
            "• <code>30-</code> — 30-soniyadan oxirigacha\n"
            "• <code>-20</code> — boshidan 20-soniyagacha\n\n"
            "Format: <code>soniya</code> yoki <code>daq:son</code> yoki <code>soat:daq:son</code>"
        ),
        "tag_title_prompt": (
            "🏷 Yangi <b>qo'shiq nomini</b> yuboring.\nHozirgi nom: <i>{current}</i>\n"
            "O'zgartirmaslik uchun <code>-</code> yuboring."
        ),
        "tag_artist_prompt": (
            "👤 Endi <b>artist nomini</b> yuboring.\nHozirgi artist: <i>{current}</i>\n"
            "O'zgartirmaslik uchun <code>-</code> yuboring."
        ),
        "lang_choose": "🌐 Tilni tanlang / Выберите язык / Choose language:",
        "lang_set": "✅ Til o'zgartirildi: O'zbekcha",
        # xatolar
        "err_time_format": "Vaqt formati noto'g'ri.",
        "err_range_format": "Format: <code>0:10-0:45</code> yoki <code>10-45</code>",
        "err_end_before_start": "Tugash vaqti boshlanish vaqtidan katta bo'lishi kerak.",
        "err_timeout": "Ishlov berish juda uzoq davom etdi, qayta urinib ko'ring.",
        "err_ffmpeg": "Faylni qayta ishlab bo'lmadi (format qo'llab-quvvatlanmaydi yoki fayl buzilgan).",
        "err_duration": "Audio davomiyligini aniqlab bo'lmadi.",
        "err_start_after_end": "Boshlanish vaqti audio uzunligidan ({total} s) katta.",
    },
    "ru": {
        "start": (
            "👋 Привет, <b>{name}</b>!\n\n"
            "Я бот для редактирования аудио и музыки. Отправьте мне файл <b>MP3, M4A, OGG, WAV</b> "
            "или <b>голосовое сообщение</b>, и я смогу:\n\n"
            "✂️ <b>Обрезать</b> — вырезать нужную часть аудио\n"
            "🔊 <b>Громкость</b> — сделать звук громче или тише\n"
            "🏷 <b>Название / Исполнитель</b> — изменить ID3-теги\n"
            "📉 <b>Размер / Битрейт</b> — уменьшить размер файла\n"
            "🖼 <b>Обложка</b> — добавить картинку к аудио\n\n"
            "🌐 Сменить язык: /language\n\n"
            "Чтобы начать, отправьте аудио 🎧"
        ),
        "btn_trim": "✂️ Обрезать (Trim)",
        "btn_volume": "🔊 Громкость",
        "btn_tags": "🏷 Название / Исполнитель (ID3)",
        "btn_bitrate": "📉 Размер / Битрейт",
        "btn_cover": "🖼 Обложка (картинка)",
        "btn_lang": "🌐 Язык",
        "btn_back": "⬅️ Назад",
        "btn_cancel": "❌ Отмена",
        "send_audio_first": "Сначала отправьте аудио 🎧",
        "audio_received": "🎧 Аудио получено. Что будем делать?",
        "processing": "⏳ Обработка…",
        "generic_error": "❌ Произошла ошибка. Попробуйте другой файл.",
        "cancelled_msg": "Отменено. Отправьте аудио или воспользуйтесь кнопками.",
        "cancelled_cb": "Отменено",
        "wrong_file": "⚠️ Пожалуйста, отправьте аудиофайл (MP3, M4A, OGG, WAV) или голосовое сообщение.",
        "file_too_big": "⚠️ Файл слишком большой. Максимальный размер — 20 МБ.",
        "cover_prompt": "🖼 Отправьте <b>картинку</b> для обложки (как фото или как файл).",
        "cover_not_image": "⚠️ Пожалуйста, отправьте изображение (JPG, PNG).",
        "cover_too_big": "⚠️ Изображение слишком большое (максимум 20 МБ).",
        "cover_need_image": "🖼 Отправьте изображение или нажмите ❌ Отмена.",
        "trim_prompt": (
            "✂️ Какую часть оставить? Отправьте промежуток времени:\n\n"
            "• <code>0:10-0:45</code> — с 10-й по 45-ю секунду\n"
            "• <code>30-</code> — с 30-й секунды до конца\n"
            "• <code>-20</code> — с начала до 20-й секунды\n\n"
            "Формат: <code>сек</code> или <code>мин:сек</code> или <code>час:мин:сек</code>"
        ),
        "tag_title_prompt": (
            "🏷 Отправьте новое <b>название трека</b>.\nСейчас: <i>{current}</i>\n"
            "Чтобы не менять, отправьте <code>-</code>."
        ),
        "tag_artist_prompt": (
            "👤 Теперь отправьте <b>имя исполнителя</b>.\nСейчас: <i>{current}</i>\n"
            "Чтобы не менять, отправьте <code>-</code>."
        ),
        "lang_choose": "🌐 Tilni tanlang / Выберите язык / Choose language:",
        "lang_set": "✅ Язык изменён: Русский",
        "err_time_format": "Неверный формат времени.",
        "err_range_format": "Формат: <code>0:10-0:45</code> или <code>10-45</code>",
        "err_end_before_start": "Время окончания должно быть больше времени начала.",
        "err_timeout": "Обработка заняла слишком много времени, попробуйте ещё раз.",
        "err_ffmpeg": "Не удалось обработать файл (формат не поддерживается или файл повреждён).",
        "err_duration": "Не удалось определить длительность аудио.",
        "err_start_after_end": "Время начала больше длины аудио ({total} с).",
    },
    "en": {
        "start": (
            "👋 Hello, <b>{name}</b>!\n\n"
            "I'm a bot for editing audio and music files. Send me a <b>MP3, M4A, OGG, WAV</b> "
            "file or a <b>voice message</b> and I can:\n\n"
            "✂️ <b>Trim</b> — cut out the part of the audio you need\n"
            "🔊 <b>Volume</b> — make the sound louder or quieter\n"
            "🏷 <b>Title / Artist</b> — change ID3 tags\n"
            "📉 <b>Size / Bitrate</b> — make the file smaller\n"
            "🖼 <b>Cover</b> — add a picture to the audio\n\n"
            "🌐 Change language: /language\n\n"
            "Send an audio file to get started 🎧"
        ),
        "btn_trim": "✂️ Trim",
        "btn_volume": "🔊 Volume",
        "btn_tags": "🏷 Title / Artist (ID3)",
        "btn_bitrate": "📉 Size / Bitrate",
        "btn_cover": "🖼 Cover (image)",
        "btn_lang": "🌐 Language",
        "btn_back": "⬅️ Back",
        "btn_cancel": "❌ Cancel",
        "send_audio_first": "Send an audio file first 🎧",
        "audio_received": "🎧 Audio received. What shall we do?",
        "processing": "⏳ Processing…",
        "generic_error": "❌ Something went wrong. Try another file.",
        "cancelled_msg": "Cancelled. Send an audio file or use the buttons.",
        "cancelled_cb": "Cancelled",
        "wrong_file": "⚠️ Please send an audio file (MP3, M4A, OGG, WAV) or a voice message.",
        "file_too_big": "⚠️ The file is too large. Maximum size is 20 MB.",
        "cover_prompt": "🖼 Send the <b>image</b> you want as the cover (as a photo or as a file).",
        "cover_not_image": "⚠️ Please send an image (JPG, PNG).",
        "cover_too_big": "⚠️ The image is too large (maximum 20 MB).",
        "cover_need_image": "🖼 Please send an image or press ❌ Cancel.",
        "trim_prompt": (
            "✂️ Which part should I keep? Send a time range:\n\n"
            "• <code>0:10-0:45</code> — from second 10 to second 45\n"
            "• <code>30-</code> — from second 30 to the end\n"
            "• <code>-20</code> — from the start to second 20\n\n"
            "Format: <code>sec</code> or <code>min:sec</code> or <code>hour:min:sec</code>"
        ),
        "tag_title_prompt": (
            "🏷 Send the new <b>track title</b>.\nCurrent: <i>{current}</i>\n"
            "Send <code>-</code> to keep it unchanged."
        ),
        "tag_artist_prompt": (
            "👤 Now send the <b>artist name</b>.\nCurrent: <i>{current}</i>\n"
            "Send <code>-</code> to keep it unchanged."
        ),
        "lang_choose": "🌐 Tilni tanlang / Выберите язык / Choose language:",
        "lang_set": "✅ Language changed: English",
        "err_time_format": "Invalid time format.",
        "err_range_format": "Format: <code>0:10-0:45</code> or <code>10-45</code>",
        "err_end_before_start": "The end time must be greater than the start time.",
        "err_timeout": "Processing took too long, please try again.",
        "err_ffmpeg": "Could not process the file (unsupported format or the file is corrupted).",
        "err_duration": "Could not determine the audio duration.",
        "err_start_after_end": "The start time is beyond the audio length ({total} s).",
    },
}


def t(lang: str, key: str, **kw) -> str:
    text = TEXTS.get(lang, TEXTS[DEFAULT_LANG]).get(key) or TEXTS[DEFAULT_LANG][key]
    return text.format(**kw) if kw else text


# ------------------------------------------------ foydalanuvchi tilini saqlash
_PATH = Path(__file__).resolve().parent / "user_langs.json"
_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _cache = {}
        except Exception:
            log.exception("user_langs.json o'qilmadi, bo'sh bilan davom etamiz")
            _cache = {}
    return _cache


def guess_lang(tg_code: str | None) -> str:
    code = (tg_code or "").lower()
    if code.startswith("ru"):
        return "ru"
    if code.startswith("en"):
        return "en"
    return DEFAULT_LANG


def get_lang(user_id: int, tg_code: str | None = None) -> str:
    """Saqlangan til; bo'lmasa Telegram tilidan taxmin qilinadi (ru/en), aks holda uz."""
    saved = _load().get(str(user_id))
    return saved if saved in TEXTS else guess_lang(tg_code)


def set_lang(user_id: int, lang: str) -> None:
    if lang not in TEXTS:
        return
    data = _load()
    data[str(user_id)] = lang
    try:
        tmp = _PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, _PATH)  # atomik yozish
    except Exception:
        log.exception("Tilni saqlab bo'lmadi")
