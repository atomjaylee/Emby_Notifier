from emby_notifier.clients.telegram import TelegramClient


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


class FakeSession:
    def __init__(self):
        self.posts = []

    def post(self, url, json=None, timeout=None):
        self.posts.append((url, json, timeout))
        return FakeResponse()


def test_send_photo_can_show_caption_above_media():
    client = TelegramClient("token", "chat-id", timeout=9)
    client.session = FakeSession()

    client.send_photo("caption", "photo-url", show_caption_above_media=True)

    assert client.session.posts == [
        (
            "https://api.telegram.org/bottoken/sendPhoto",
            {
                "chat_id": "chat-id",
                "photo": "photo-url",
                "caption": "caption",
                "parse_mode": "Markdown",
                "show_caption_above_media": True,
            },
            9,
        )
    ]
