"""ffmpeg orqali audio bilan ishlash (asinxron, botni bloklamaydi)."""
import asyncio
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Bir vaqtning o'zida ko'pi bilan 2 ta ffmpeg jarayoni (server yuklanmasligi uchun)
_sem = asyncio.Semaphore(2)
_TIMEOUT = 300  # soniya


class AudioError(Exception):
    """Foydalanuvchiga ko'rsatish mumkin bo'lgan xato.

    Matn emas, i18n kaliti (+ parametrlar) saqlanadi — handlers uni foydalanuvchi
    tiliga tarjima qiladi.
    """

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params


async def _run(cmd: list[str]) -> str:
    async with _sem:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), _TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            raise AudioError("err_timeout")
    if proc.returncode != 0:
        log.error("ffmpeg xatosi: %s", err.decode(errors="ignore")[-800:])
        raise AudioError("err_ffmpeg")
    return out.decode(errors="ignore")


def _ffmpeg(src: Path) -> list[str]:
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src)]


def _mp3(kbps: int = 192) -> list[str]:
    # Muqova (rasm) bo'lsa, u saqlanib qoladi: "0:v?" — mavjud bo'lsa olinadi
    return [
        "-map", "0:a", "-map", "0:v?",
        "-c:a", "libmp3lame", "-b:a", f"{kbps}k",
        "-c:v", "copy", "-id3v2_version", "3",
    ]


async def duration(path: Path) -> float:
    out = await _run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    try:
        return float(out.strip())
    except ValueError:
        raise AudioError("err_duration")


async def trim(src: Path, dst: Path, start: float, end: float | None) -> None:
    total = await duration(src)
    if start >= total:
        raise AudioError("err_start_after_end", total=f"{total:.1f}")
    end = total if end is None else min(end, total)
    # -ss ni -i dan OLDIN beramiz: shunda muqova (rasm) oqimi yo'qolmaydi
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{end - start:.3f}",
    ]
    await _run(cmd + _mp3(192) + [str(dst)])


async def change_volume(src: Path, dst: Path, percent: int) -> None:
    factor = percent / 100
    filt = f"volume={factor:.3f}"
    if factor > 1:
        filt += ",alimiter=limit=0.95"  # buzilib ketmasligi uchun
    await _run(_ffmpeg(src) + ["-af", filt] + _mp3(192) + [str(dst)])


async def set_tags(src: Path, dst: Path, title: str, artist: str) -> None:
    cmd = _ffmpeg(src)
    if src.suffix.lower() == ".mp3":
        # Qayta kodlamasdan, sifat yo'qolmaydi, muqova (cover) saqlanadi
        cmd += ["-map", "0", "-c", "copy", "-id3v2_version", "3"]
    else:
        cmd += _mp3(192)
    if title:
        cmd += ["-metadata", f"title={title}"]
    if artist:
        cmd += ["-metadata", f"artist={artist}"]
    await _run(cmd + [str(dst)])


async def change_bitrate(src: Path, dst: Path, kbps: int) -> None:
    await _run(_ffmpeg(src) + _mp3(kbps) + [str(dst)])


async def set_cover(src: Path, dst: Path, image: Path) -> None:
    """Audioga muqova (album art) o'rnatadi. Telegram uchun thumb.jpg ham yaratadi."""
    cmd = _ffmpeg(src) + ["-i", str(image), "-map", "0:a", "-map", "1:0"]
    if src.suffix.lower() == ".mp3":
        cmd += ["-c:a", "copy"]  # audio qayta kodlanmaydi
    else:
        cmd += ["-c:a", "libmp3lame", "-b:a", "192k"]
    cmd += [
        "-c:v", "mjpeg", "-q:v", "2",
        "-vf", "scale='min(1000,iw)':-2",
        "-id3v2_version", "3",
        "-metadata:s:v", "title=Album cover",
        "-metadata:s:v", "comment=Cover (front)",
        str(dst),
    ]
    await _run(cmd)

    # Telegram pleyeri uchun kichik eskiz (JPEG, 320px gacha)
    await _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(image),
        "-vf", "scale=320:320:force_original_aspect_ratio=decrease",
        "-q:v", "5", "-frames:v", "1", str(dst.parent / "thumb.jpg"),
    ])
