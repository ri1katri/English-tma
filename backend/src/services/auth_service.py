import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl


def validate_telegram_init_data(
    init_data_raw: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> Optional[Dict[str, Any]]:
    """
    Валидация Telegram Mini App initData по официальной спецификации HMAC-SHA256:
    1. Парсинг querystring.
    2. Извлечение hash.
    3. Сортировка параметров и формирование data_check_string.
    4. secret_key = HMAC_SHA256(b"WebAppData", bot_token.encode()).
    5. calculated_hash = HMAC_SHA256(secret_key, data_check_string).hexdigest().
    6. hmac.compare_digest(calculated_hash, received_hash).
    7. Проверка auth_date на срок давности (max_age_seconds).
    8. Возврат распарсенного словаря пользователя Telegram.
    """
    # Без токена подпись проверить невозможно — считаем данные невалидными.
    # (Пустой токен нельзя превращать в «известный всем» секрет.)
    if not init_data_raw or not bot_token:
        return None

    try:
        parsed_data = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    except Exception:
        return None

    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        return None

    auth_date_str = parsed_data.get("auth_date")
    if not auth_date_str:
        return None

    try:
        auth_date = int(auth_date_str)
    except ValueError:
        return None

    current_time = int(time.time())
    if current_time - auth_date > max_age_seconds:
        return None

    # Сортировка по алфавиту ключей
    items = sorted(parsed_data.items(), key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)

    # Генерация secret_key
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # Вычисление проверочного хеша
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    user_raw = parsed_data.get("user")
    if not user_raw:
        return None

    try:
        user_dict = json.loads(user_raw)
    except Exception:
        return None

    return user_dict


def extract_telegram_id(tg_user: Any) -> Optional[int]:
    """
    Достаёт числовой Telegram ID из уже проверенного (по подписи) объекта user.
    Возвращает None, если структура неожиданная.
    """
    if not isinstance(tg_user, dict):
        return None
    raw_id = tg_user.get("id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id <= 0:
        return None
    return raw_id
