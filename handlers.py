import contextlib
import html
import logging
import re
import tempfile
from pathlib import Path
from typing import Awaitable, Callable

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message, User

import audio_utils as au
import keyboards as kb
from i18n import LANG_NAMES, get_lang, set_lang, t

log = logging.getLogger(__name__)
router = Router()

MAX_SIZE = 20 * 1024 * 1024  # Bot API orqali yuklab olish chegarasi (20 MB)
AUDIO_EXT = {".mp3", ".m4a", ".ogg", ".oga", ".opus", ".wav"}

Job = Callable[[Path, Path], Awaitable[None]]


class Edit(StatesGroup):
    trim = State()
    tag_title = State()
    tag_artist = State()
    cover = State()


def lang_of(user: User | None) -> str:
    """Foydalanuvchi tili: saqlangan bo'lsa shu, bo'lmasa Telegram tilidan taxmin."""
    if user is None:
        return "uz"
    return get_lang(user.id, user.language_code)


# ---------------------------------------------------------------- yordamchilar
_TIME_RE = re.compile(r"\d+(\.\d+)?(:\d+(\.\d+)?){0,2}")


def parse_time(s: str) -> float:
    s = s.strip().replace(",", ".")
    if not _TIME_RE.fullmatch(s):
        raise ValueError("err_time_format")
    total = 0.0
    for part in s.split(":"):
        total = total * 60 + float(part)
    return total


def parse_range(text: str) -> tuple[float, float | None]:
    """'10-45', '0:10 - 1:05', '30-' (oxirigacha), '-20' (boshidan 20 s gacha).

    Xatoda ValueError(<i18n kaliti>) ko'taradi.
    """
    parts = re.split(r"\s*[-–—]\s*|\s+", text.strip())
    if len(parts) != 2 or not any(parts):
        raise ValueError("err_range_format")
    start = parse_time(parts[0]) if parts[0] else 0.0
    end = parse_time(parts[1]) if parts[1] else None
    if end is not None and end <= start:
        raise ValueError("err_end_before_start")
    return start, end


def make_filename(title: str | None, performer: str | None, fallback: str) -> str:
    base = f"{performer} - {title}" if title and performer else (title or Path(fallback).stem)
    base = re.sub(r'[\\/:*?"<>|\r\n]+', " ", base).strip()[:80] or "audio"
    return base + ".mp3"


async def ensure_file(call: CallbackQuery, state: FSMContext) -> bool:
    if "file_id" in await state.get_data():
        return True
    await call.answer(t(lang_of(call.from_user), "send_audio_first"), show_alert=True)
    return False


async def run_job(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    job: Job,
    lang: str,
    *,
    title: str | None = None,
    performer: str | None = None,
) -> None:
    """Faylni yuklab oladi, job'ni bajaradi, natijani yuboradi va holatni yangilaydi."""
    data = await state.get_data()
    title = data.get("title") if title is None else title
    performer = data.get("performer") if performer is None else performer

    status = await bot.send_message(chat_id, t(lang, "processing"))
    sent: Message | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="mp3bot_") as tmp_name:
            tmp = Path(tmp_name)
            src = tmp / ("input" + (Path(data["file_name"]).suffix or ".bin"))
            dst = tmp / "output.mp3"

            await bot.download(data["file_id"], destination=src)
            await job(src, dst)

            size_mb = dst.stat().st_size / 1024 / 1024
            thumb = dst.parent / "thumb.jpg"
            sent = await bot.send_audio(
                chat_id,
                FSInputFile(dst, filename=make_filename(title, performer, data["file_name"])),
                thumbnail=FSInputFile(thumb) if thumb.exists() else None,
                title=title,
                performer=performer,
                caption=f"📦 {size_mb:.2f} MB",
                reply_markup=kb.main_menu(lang),
            )
    except au.AudioError as e:
        await bot.send_message(chat_id, "❌ " + t(lang, e.key, **e.params))
    except Exception:
        log.exception("Ishda xatolik")
        await bot.send_message(chat_id, t(lang, "generic_error"))
    finally:
        with contextlib.suppress(Exception):
            await status.delete()

    if sent and sent.audio:
        # Natija yangi "joriy fayl" bo'ladi — shu ustida davom etish mumkin
        await state.set_state(None)
        await state.update_data(
            file_id=sent.audio.file_id,
            file_name=sent.audio.file_name or "audio.mp3",
            title=title,
            performer=performer,
        )


# ---------------------------------------------------------------- buyruqlar
# DIQQAT: buyruqlar (start, cancel, language) holat handlerlaridan OLDIN turishi kerak,
# aks holda FSM holatidagi F.text handler ularni oddiy matn deb yeb qo'yadi.
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    lang = lang_of(message.from_user)
    name = message.from_user.full_name if message.from_user else "👋"
    await message.answer(t(lang, "start", name=html.escape(name)))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.set_state(None)
    await message.answer(t(lang_of(message.from_user), "cancelled_msg"))


# ---------------------------------------------------------------- Til tanlash
@router.message(Command("language", "lang", "til"))
async def cmd_language(message: Message):
    lang = lang_of(message.from_user)
    await message.answer(t(lang, "lang_choose"), reply_markup=kb.lang_menu(lang))


@router.callback_query(F.data == "act:lang")
async def open_language(call: CallbackQuery, bot: Bot):
    lang = lang_of(call.from_user)
    await bot.send_message(call.from_user.id, t(lang, "lang_choose"), reply_markup=kb.lang_menu(lang))
    await call.answer()


@router.callback_query(F.data.startswith("lang:"))
async def set_language(call: CallbackQuery):
    code = call.data.split(":")[1]
    if code not in LANG_NAMES:
        await call.answer()
        return
    set_lang(call.from_user.id, code)
    with contextlib.suppress(Exception):
        await call.message.edit_text(t(code, "lang_set"), reply_markup=kb.lang_menu(code))
    await call.answer()


# ---------------------------------------------------------------- Muqova (rasm)
# DIQQAT: bu handler on_audio'dan OLDIN turishi kerak, aks holda rasm-hujjat
# on_audio'ga tushib ketadi.
@router.callback_query(F.data == "act:cover")
async def cover_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await ensure_file(call, state):
        return
    lang = lang_of(call.from_user)
    await state.set_state(Edit.cover)
    await bot.send_message(call.from_user.id, t(lang, "cover_prompt"), reply_markup=kb.cancel_kb(lang))
    await call.answer()


@router.message(Edit.cover, F.photo | F.document)
async def cover_apply(message: Message, state: FSMContext, bot: Bot):
    lang = lang_of(message.from_user)
    if message.photo:
        img = message.photo[-1]  # eng katta o'lcham
    else:
        img = message.document
        if not (img.mime_type or "").startswith("image/"):
            await message.answer(t(lang, "cover_not_image"))
            return
    if img.file_size and img.file_size > MAX_SIZE:
        await message.answer(t(lang, "cover_too_big"))
        return

    async def job(src: Path, dst: Path) -> None:
        image_path = src.parent / "cover.img"
        await bot.download(img.file_id, destination=image_path)
        await au.set_cover(src, dst, image_path)

    await run_job(bot, message.chat.id, state, job, lang)


@router.message(Edit.cover, F.text)
async def cover_wrong(message: Message):
    await message.answer(t(lang_of(message.from_user), "cover_need_image"))


# ---------------------------------------------------------------- audio qabul qilish
@router.message(F.audio | F.voice | F.document)
async def on_audio(message: Message, state: FSMContext):
    lang = lang_of(message.from_user)
    title = performer = None
    if message.audio:
        f = message.audio
        name = f.file_name or "audio.mp3"
        title, performer = f.title, f.performer
    elif message.voice:
        f = message.voice
        name = "voice.ogg"
    else:
        f = message.document
        name = f.file_name or ""
        is_audio = Path(name).suffix.lower() in AUDIO_EXT or (f.mime_type or "").startswith("audio/")
        if not is_audio:
            await message.answer(t(lang, "wrong_file"))
            return

    if f.file_size and f.file_size > MAX_SIZE:
        await message.answer(t(lang, "file_too_big"))
        return

    await state.clear()
    await state.update_data(file_id=f.file_id, file_name=name, title=title, performer=performer)
    await message.reply(t(lang, "audio_received"), reply_markup=kb.main_menu(lang))


# ---------------------------------------------------------------- menyu navigatsiyasi
@router.callback_query(F.data == "act:back")
async def back_to_menu(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=kb.main_menu(lang_of(call.from_user)))
    await call.answer()


@router.callback_query(F.data == "act:cancel")
async def cancel_prompt(call: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    with contextlib.suppress(Exception):
        await call.message.delete()
    await call.answer(t(lang_of(call.from_user), "cancelled_cb"))


@router.callback_query(F.data == "act:volume")
async def open_volume(call: CallbackQuery, state: FSMContext):
    if not await ensure_file(call, state):
        return
    await call.message.edit_reply_markup(reply_markup=kb.volume_menu(lang_of(call.from_user)))
    await call.answer()


@router.callback_query(F.data == "act:bitrate")
async def open_bitrate(call: CallbackQuery, state: FSMContext):
    if not await ensure_file(call, state):
        return
    await call.message.edit_reply_markup(reply_markup=kb.bitrate_menu(lang_of(call.from_user)))
    await call.answer()


# ---------------------------------------------------------------- Volume
@router.callback_query(F.data.startswith("vol:"))
async def volume_apply(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await ensure_file(call, state):
        return
    percent = int(call.data.split(":")[1])
    await call.answer()
    await run_job(
        bot, call.from_user.id, state,
        lambda s, d: au.change_volume(s, d, percent), lang_of(call.from_user),
    )


# ---------------------------------------------------------------- Bitrate
@router.callback_query(F.data.startswith("br:"))
async def bitrate_apply(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await ensure_file(call, state):
        return
    kbps = int(call.data.split(":")[1])
    await call.answer()
    await run_job(
        bot, call.from_user.id, state,
        lambda s, d: au.change_bitrate(s, d, kbps), lang_of(call.from_user),
    )


# ---------------------------------------------------------------- Trim
@router.callback_query(F.data == "act:trim")
async def trim_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await ensure_file(call, state):
        return
    lang = lang_of(call.from_user)
    await state.set_state(Edit.trim)
    await bot.send_message(call.from_user.id, t(lang, "trim_prompt"), reply_markup=kb.cancel_kb(lang))
    await call.answer()


@router.message(Edit.trim, F.text)
async def trim_apply(message: Message, state: FSMContext, bot: Bot):
    lang = lang_of(message.from_user)
    try:
        start, end = parse_range(message.text)
    except ValueError as e:
        await message.answer("❌ " + t(lang, str(e)))
        return
    await run_job(bot, message.chat.id, state, lambda s, d: au.trim(s, d, start, end), lang)


# ---------------------------------------------------------------- ID3 teglar
@router.callback_query(F.data == "act:tags")
async def tags_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await ensure_file(call, state):
        return
    lang = lang_of(call.from_user)
    data = await state.get_data()
    current = html.escape(data.get("title") or "—")
    await state.set_state(Edit.tag_title)
    await bot.send_message(
        call.from_user.id,
        t(lang, "tag_title_prompt", current=current),
        reply_markup=kb.cancel_kb(lang),
    )
    await call.answer()


@router.message(Edit.tag_title, F.text)
async def tags_title(message: Message, state: FSMContext):
    lang = lang_of(message.from_user)
    data = await state.get_data()
    await state.update_data(new_title=message.text.strip()[:128])
    await state.set_state(Edit.tag_artist)
    current = html.escape(data.get("performer") or "—")
    await message.answer(
        t(lang, "tag_artist_prompt", current=current),
        reply_markup=kb.cancel_kb(lang),
    )


@router.message(Edit.tag_artist, F.text)
async def tags_artist(message: Message, state: FSMContext, bot: Bot):
    lang = lang_of(message.from_user)
    data = await state.get_data()
    title = data.get("new_title", "-")
    artist = message.text.strip()[:128]
    if title == "-":
        title = data.get("title") or ""
    if artist == "-":
        artist = data.get("performer") or ""

    await run_job(
        bot,
        message.chat.id,
        state,
        lambda s, d: au.set_tags(s, d, title, artist),
        lang,
        title=title,
        performer=artist,
    )
