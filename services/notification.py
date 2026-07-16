import requests

TELEGRAM_LIMIT = 4096


def _split_telegram_message(message, limit=TELEGRAM_LIMIT):
    text = str(message)
    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            for idx in range(0, len(line), limit):
                chunks.append(line[idx : idx + limit])
            continue

        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line

    if current:
        chunks.append(current)
    return chunks


def send_telegram_message(bot_token, chat_id, msg):
    if not bot_token:
        return False, "TELEGRAM_BOT_TOKEN is empty"
    if not chat_id:
        return False, "TELEGRAM_CHAT_ID is empty"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        sent = 0
        for chunk in _split_telegram_message(msg):
            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if not response.ok:
                return False, f"Telegram API error {response.status_code}: {response.text}"
            sent += 1
        return True, f"Telegram message sent ({sent} part{'s' if sent != 1 else ''})"
    except Exception as exc:
        return False, f"Telegram request failed: {exc}"
