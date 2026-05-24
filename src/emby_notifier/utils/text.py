TELEGRAM_MARKDOWN_ESCAPE_CHARS = ("_", "*", "`", "[")


def escape_telegram_markdown(text: object) -> str:
    escaped = "" if text is None else str(text)
    for char in TELEGRAM_MARKDOWN_ESCAPE_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped
