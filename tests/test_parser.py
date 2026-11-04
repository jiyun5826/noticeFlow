from src.main import parse_notices
import pytest


RSS_XML = """
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>테스트 일반공지</title>
      <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&amp;seq=12345&amp;sort=7</link>
      <pubDate>2026-11-04 12:30:00</pubDate>
    </item>
  </channel>
</rss>
""".strip().encode("utf-8")


def test_parse_notices_extracts_normalized_fields():
    notices = parse_notices(RSS_XML)

    assert notices == [
        {
            "source": "uos_general",
            "source_id": "12345",
            "title": "테스트 일반공지",
            "url": "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&seq=12345&sort=7",
            "published_at": "2026-11-04 12:30:00",
        }
    ]

def test_parse_notices_rejects_wrong_board():
    invalid_xml = """
    <rss>
      <channel>
        <item>
          <title>다른 게시판 공지</title>
          <link>https://www.uos.ac.kr/korNotice/view.do?list_id=OTHER&amp;seq=999</link>
          <pubDate>2026-11-04 12:30:00</pubDate>
        </item>
      </channel>
    </rss>
    """.strip().encode("utf-8")

    with pytest.raises(ValueError, match="일반공지 링크 형식"):
        parse_notices(invalid_xml)


def test_parse_notices_rejects_feed_without_items():
    empty_feed = b"<rss><channel></channel></rss>"

    with pytest.raises(ValueError, match="공지 항목"):
        parse_notices(empty_feed)
