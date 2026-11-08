from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import LANG_NAMES, t


def main_menu(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_trim"), callback_data="act:trim")
    b.button(text=t(lang, "btn_volume"), callback_data="act:volume")
    b.button(text=t(lang, "btn_tags"), callback_data="act:tags")
    b.button(text=t(lang, "btn_bitrate"), callback_data="act:bitrate")
    b.button(text=t(lang, "btn_cover"), callback_data="act:cover")
    b.button(text=t(lang, "btn_lang"), callback_data="act:lang")
    b.adjust(2, 2, 2)
    return b.as_markup()


def volume_menu(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in (25, 50, 75, 150, 200, 300):
        b.button(text=f"{p}%", callback_data=f"vol:{p}")
    b.button(text=t(lang, "btn_back"), callback_data="act:back")
    b.adjust(3, 3, 1)
    return b.as_markup()


def bitrate_menu(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for k in (64, 96, 128, 192, 256, 320):
        b.button(text=f"{k} kbps", callback_data=f"br:{k}")
    b.button(text=t(lang, "btn_back"), callback_data="act:back")
    b.adjust(3, 3, 1)
    return b.as_markup()


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_cancel"), callback_data="act:cancel")
    return b.as_markup()


def lang_menu(current: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, name in LANG_NAMES.items():
        mark = "✅ " if code == current else ""
        b.button(text=f"{mark}{name}", callback_data=f"lang:{code}")
    b.adjust(1)
    return b.as_markup()
