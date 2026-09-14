from django.test import SimpleTestCase

from quizzly_app.api.serializers import YoutubeUrlSerializer

VIDEO_ID = "abcdefghijk"


class YoutubeUrlSerializerTests(SimpleTestCase):
    """Cover the URL check that guards the quiz generation."""

    def is_valid(self, url):
        return YoutubeUrlSerializer(data={"url": url}).is_valid()

    def test_accepts_watch_url(self):
        url = f"https://www.youtube.com/watch?v={VIDEO_ID}"

        self.assertTrue(self.is_valid(url))

    def test_rejects_plain_http(self):
        url = f"http://www.youtube.com/watch?v={VIDEO_ID}"

        self.assertFalse(self.is_valid(url))

    def test_rejects_other_hosts(self):
        self.assertFalse(self.is_valid("https://vimeo.com/123456"))

    def test_rejects_short_links(self):
        # youtu.be and the mobile site are deliberately unsupported
        self.assertFalse(self.is_valid(f"https://youtu.be/{VIDEO_ID}"))
        self.assertFalse(
            self.is_valid(f"https://m.youtube.com/watch?v={VIDEO_ID}")
        )

    def test_rejects_missing_url(self):
        self.assertFalse(YoutubeUrlSerializer(data={}).is_valid())
