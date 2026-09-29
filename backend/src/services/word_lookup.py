"""
Поиск слова: нормализация ввода, два бесплатных внешних словаря (primary + fallback,
оба без API-ключа) и преобразование ответа в нашу модель (words + word_senses).

Модуль не работает с БД. Правила:
  * внешний провайдер русских переводов НЕ даёт — translations_ru всегда пустой;
    английское слово никогда не выдаётся за русский перевод;
  * «слово не найдено» (провайдер ответил, что такого слова нет) и «провайдер
    недоступен» (таймаут, сетевая ошибка, 429, 5xx, 522, мусор в ответе) —
    разные результаты;
  * DB -> primary provider -> fallback provider. words.py об этом не знает:
    fetch_external_entries() снаружи выглядит как один провайдер.
"""
import html
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Primary: Free Dictionary API. Fallback: Wiktionary REST API (en.wiktionary.org,
# официальный эндпоинт MediaWiki/Wikimedia, без ключа и без регистрации).
# Внешний контракт fetch_external_entries() не меняется: words.py по-прежнему
# получает ExternalLookup и отдаёт entries в parse_entries() как раньше.
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
WIKTIONARY_API_URL = "https://en.wiktionary.org/api/rest_v1/page/definition/{word}"
REQUEST_TIMEOUT_SECONDS = 6.0

# Wikimedia REST API (en.wiktionary.org) требует информативный User-Agent —
# запросы с генерическим/дефолтным UA (например, дефолт самой httpx) политика
# Wikimedia блокирует, и это выглядит как HTTP 403 "как будто нет доступа",
# хотя реальная причина — отсутствие опознавательного заголовка, а не сам
# запрос или слово. Формат — рекомендованный Wikimedia:
# "<client>/<version> (<contact/site>) <library>/<version>".
# dictionaryapi.dev такого требования не выдвигает, но отправлять
# информативный UA туда тоже правильно и безопасно, поэтому используем один
# и тот же заголовок для обоих провайдеров.
USER_AGENT = (
    "english-tma/1.0 "
    "(https://github.com/ri1katri/English-tma; dictionary lookup for a Telegram Mini App) "
    f"httpx/{httpx.__version__}"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}

MAX_LEMMA_LENGTH = 128  # words.lemma = String(128)
MAX_POS_LENGTH = 32  # word_senses.part_of_speech = String(32)
MAX_TRANSCRIPTION_LENGTH = 128  # word_senses.transcription = String(128)
MAX_DEFINITIONS_PER_MEANING = 2
MAX_SENSES = 10
MAX_SYNONYMS = 4
DEFAULT_POS = "other"


# --------------------------------------------------------------------------- #
# Нормализация ввода (без изменений)
# --------------------------------------------------------------------------- #
class InvalidWordError(ValueError):
    """Ввод нельзя считать английским словом."""


_LETTERS = "a-zà-öø-ÿ"  # латиница (в т.ч. с диакритикой: café, naïve)
_WORD_RE = re.compile(rf"[{_LETTERS}]+(?:[ '\-][{_LETTERS}]+)*")
_CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)


def normalize_lemma(raw: Optional[str]) -> str:
    """
    'Apple', 'APPLE', '  apple ' -> 'apple' (один ключ глобального кэша).
    Лемматизации (ran -> run) здесь нет: это отдельный этап.
    """
    text = unicodedata.normalize("NFKC", raw or "")
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"\s+", " ", text).strip().lower()
    if not text or len(text) > MAX_LEMMA_LENGTH or not _WORD_RE.fullmatch(text):
        raise InvalidWordError("Not a valid English word")
    return text


# --------------------------------------------------------------------------- #
# Внешние провайдеры
# --------------------------------------------------------------------------- #
class LookupStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"  # провайдер ответил: такого слова нет
    UNAVAILABLE = "unavailable"  # провайдер не смог ответить


@dataclass
class ExternalLookup:
    status: LookupStatus
    entries: List[dict] = field(default_factory=list)


async def _get_json(url: str, *, provider: str, lemma: str):
    """
    Общий HTTP-вызов для обоих провайдеров.
    Возвращает (status, payload): status уже готовый LookupStatus для
    сетевых ошибок/таймаута/404/не-200/битого JSON; payload не None только
    когда есть смысл разбирать ответ дальше (200 + валидный JSON).
    """
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=REQUEST_HEADERS,
        ) as client:
            resp = await client.get(url)
    except httpx.TimeoutException:
        logger.warning("%s provider timeout for %r", provider, lemma)
        return LookupStatus.UNAVAILABLE, None
    except httpx.HTTPError as exc:
        logger.warning(
            "%s provider request failed for %r: %s", provider, lemma, type(exc).__name__
        )
        return LookupStatus.UNAVAILABLE, None

    if resp.status_code == 404:
        return LookupStatus.NOT_FOUND, None
    if resp.status_code != 200:
        # 429, любые 5xx (включая нестандартный Cloudflare 522) и прочие
        # неожиданные коды — это проблема провайдера, а не слова.
        logger.warning(
            "%s provider returned HTTP %s for %r", provider, resp.status_code, lemma
        )
        return LookupStatus.UNAVAILABLE, None

    try:
        data = resp.json()
    except ValueError:
        logger.warning("%s provider returned non-JSON for %r", provider, lemma)
        return LookupStatus.UNAVAILABLE, None

    return None, data


async def _fetch_primary_entries(lemma: str) -> ExternalLookup:
    """Free Dictionary API. Формат ответа — наш «родной» формат entries."""
    url = DICTIONARY_API_URL.format(word=quote(lemma, safe=""))
    status, data = await _get_json(url, provider="Primary (dictionaryapi.dev)", lemma=lemma)
    if status is not None:
        return ExternalLookup(status)

    if not isinstance(data, list):
        logger.warning("Primary provider returned unexpected payload for %r", lemma)
        return ExternalLookup(LookupStatus.UNAVAILABLE)

    entries = [e for e in data if isinstance(e, dict)]
    if not entries:
        return ExternalLookup(LookupStatus.NOT_FOUND)
    return ExternalLookup(LookupStatus.FOUND, entries)


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: Any) -> Optional[str]:
    """Wiktionary отдаёт определения/примеры как HTML-фрагменты."""
    if not isinstance(text, str):
        return None
    clean = html.unescape(_TAG_RE.sub("", text))
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or None


def _wiktionary_to_entries(payload: Any) -> List[dict]:
    """
    Адаптер: ответ Wiktionary REST API -> тот же формат entries, что и у
    Free Dictionary API (список entry с ключом "meanings"), чтобы
    parse_entries() не нужно было дублировать или менять.
    Wiktionary REST API не даёт транскрипцию/synonyms на этом эндпоинте,
    поэтому соответствующие поля просто отсутствуют — parse_entries()
    и так трактует их как Optional/пустые.
    """
    if not isinstance(payload, dict):
        return []
    en_section = payload.get("en")
    if not isinstance(en_section, list):
        return []

    meanings = []
    for block in en_section:
        if not isinstance(block, dict):
            continue
        pos = _strip_html(block.get("partOfSpeech"))
        pos = pos.lower() if pos else DEFAULT_POS
        definitions = []
        for d in block.get("definitions") or []:
            if not isinstance(d, dict):
                continue
            text = _strip_html(d.get("definition"))
            if not text:
                continue
            examples = d.get("examples") or []
            example = None
            if isinstance(examples, list):
                for ex in examples:
                    example = _strip_html(ex)
                    if example:
                        break
            # Wiktionary не даёт structured synonyms на этом эндпоинте.
            definitions.append({"definition": text, "example": example, "synonyms": []})
        if definitions:
            meanings.append({"partOfSpeech": pos, "definitions": definitions})

    if not meanings:
        return []
    # Один "entry" без phonetic/phonetics — parse_entries() корректно
    # обработает их отсутствие (транскрипция останется None).
    return [{"meanings": meanings}]


async def _fetch_fallback_entries(lemma: str) -> ExternalLookup:
    """Wiktionary REST API, бесплатный, без ключа и без регистрации."""
    url = WIKTIONARY_API_URL.format(word=quote(lemma, safe=""))
    status, data = await _get_json(url, provider="Fallback (Wiktionary)", lemma=lemma)
    if status is not None:
        return ExternalLookup(status)

    entries = _wiktionary_to_entries(data)
    if not entries:
        return ExternalLookup(LookupStatus.NOT_FOUND)
    return ExternalLookup(LookupStatus.FOUND, entries)


async def fetch_external_entries(lemma: str) -> ExternalLookup:
    """
    DB -> primary -> fallback. Внешний контракт (сигнатура, ExternalLookup,
    LookupStatus) не изменился — words.py вызывает эту функцию как раньше.

      * primary FOUND               -> сразу отдаём primary, fallback не трогаем.
      * primary UNAVAILABLE          -> пробуем fallback; результат = статус fallback
                                         (fallback FOUND/NOT_FOUND/UNAVAILABLE
                                         становится итоговым результатом).
      * primary NOT_FOUND            -> на всякий случай пробуем fallback:
                                         fallback FOUND перекрывает NOT_FOUND,
                                         иначе (NOT_FOUND или UNAVAILABLE у
                                         fallback) primary уже подтвердил, что
                                         слова нет, поэтому отдаём NOT_FOUND.
      * оба провайдера UNAVAILABLE   -> UNAVAILABLE (503 provider_unavailable).
      * оба провайдера не нашли слово -> NOT_FOUND (404 word_not_found).
    """
    primary = await _fetch_primary_entries(lemma)

    if primary.status is LookupStatus.FOUND:
        return primary

    if primary.status is LookupStatus.UNAVAILABLE:
        logger.info("Dictionary primary provider unavailable for %r", lemma)
        logger.info("Trying fallback provider for %r", lemma)
        fallback = await _fetch_fallback_entries(lemma)
        logger.info(
            "Fallback provider returned %s for %r", fallback.status.value.upper(), lemma
        )
        return fallback

    # primary.status is NOT_FOUND
    logger.info("Dictionary primary provider returned NOT_FOUND for %r", lemma)
    logger.info("Trying fallback provider for %r", lemma)
    fallback = await _fetch_fallback_entries(lemma)
    logger.info(
        "Fallback provider returned %s for %r", fallback.status.value.upper(), lemma
    )
    if fallback.status is LookupStatus.FOUND:
        return fallback
    return primary  # NOT_FOUND, тем же статусом, что уже был у primary


# --------------------------------------------------------------------------- #
# Преобразование ответа провайдера в нашу модель (без изменений)
# --------------------------------------------------------------------------- #
@dataclass
class ParsedSense:
    part_of_speech: str
    transcription: Optional[str]
    definition_en: str
    example_en: Optional[str]
    synonyms: List[str]
    translations_ru: List[str] = field(default_factory=list)  # всегда пусто


def _clean_str(value: Any, max_len: Optional[int] = None) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if max_len is not None:
        value = value[:max_len].strip()
    return value or None


def _pick_transcription(entries: List[dict]) -> Optional[str]:
    for entry in entries:
        text = _clean_str(entry.get("phonetic"), MAX_TRANSCRIPTION_LENGTH)
        if text:
            return text
        for ph in entry.get("phonetics") or []:
            if isinstance(ph, dict):
                text = _clean_str(ph.get("text"), MAX_TRANSCRIPTION_LENGTH)
                if text:
                    return text
    return None


def _pick_synonyms(definition: dict, meaning: dict, lemma: str) -> List[str]:
    raw = definition.get("synonyms") or meaning.get("synonyms") or []
    result: List[str] = []
    seen = {lemma}
    for item in raw if isinstance(raw, list) else []:
        text = _clean_str(item)
        if text and text.lower() not in seen:
            seen.add(text.lower())
            result.append(text)
        if len(result) >= MAX_SYNONYMS:
            break
    return result


def parse_entries(entries: List[dict], lemma: str) -> List[ParsedSense]:
    """Пустой результат означает, что пригодных определений нет."""
    transcription = _pick_transcription(entries)
    senses: List[ParsedSense] = []
    seen = set()

    for entry in entries:
        for meaning in entry.get("meanings") or []:
            if not isinstance(meaning, dict):
                continue
            pos = _clean_str(meaning.get("partOfSpeech"), MAX_POS_LENGTH) or DEFAULT_POS
            definitions = meaning.get("definitions") or []

            taken = 0
            for d in definitions if isinstance(definitions, list) else []:
                if taken >= MAX_DEFINITIONS_PER_MEANING or len(senses) >= MAX_SENSES:
                    break
                if not isinstance(d, dict):
                    continue
                text = _clean_str(d.get("definition"))
                if not text:
                    continue
                key = (pos.lower(), text.lower())
                if key in seen:
                    continue
                seen.add(key)
                taken += 1
                senses.append(
                    ParsedSense(
                        part_of_speech=pos,
                        transcription=transcription,
                        definition_en=text,
                        example_en=_clean_str(d.get("example")),
                        synonyms=_pick_synonyms(d, meaning, lemma),
                    )
                )
            if len(senses) >= MAX_SENSES:
                return senses
    return senses


# --------------------------------------------------------------------------- #
# Защита ответа от «английского слова вместо перевода» (без изменений)
# --------------------------------------------------------------------------- #
def clean_translations_ru(values: Any) -> List[str]:
    """
    Оставляет только строки, содержащие кириллицу. Так ранее сохранённые
    в БД «переводы» вида ["apple"] (баг старого кода) не показываются пользователю.
    """
    if not isinstance(values, list):
        return []
    result: List[str] = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or not _CYRILLIC_RE.search(text):
            continue
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            result.append(text)
    return result
