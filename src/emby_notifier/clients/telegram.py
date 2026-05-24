from __future__ import annotations

import requests


class TelegramClientError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 8):
        self.chat_id = chat_id
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{bot_token}/"
        self.session = requests.Session()

    def validate_bot(self) -> None:
        self._post("getMe", {})

    def validate_chat(self) -> None:
        self._post("getChat", {"chat_id": self.chat_id})

    def send_message(self, text: str) -> None:
        self._post(
            "sendMessage",
            {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            },
        )

    def send_photo(self, caption: str, photo: str, show_caption_above_media: bool = False) -> None:
        self._post(
            "sendPhoto",
            {
                "chat_id": self.chat_id,
                "photo": photo,
                "caption": caption,
                "parse_mode": "Markdown",
                "show_caption_above_media": show_caption_above_media,
            },
        )

    def _post(self, method: str, payload: dict) -> dict:
        try:
            response = self.session.post(
                f"{self.base_url}{method}",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TelegramClientError(f"Telegram API {method} failed: {exc}") from exc

        data = response.json()
        if not data.get("ok", False):
            raise TelegramClientError(f"Telegram API {method} failed: {data}")
        return data
