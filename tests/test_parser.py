from src.main import parse_notices, parse_published_at
import pytest


RSS_XML = """
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>테스트 일반공지</title>
      <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&amp;seq=12345&amp;sort=7</link>
      <pubDate>2026-11-04 12:30:00</pubDate>
      <description><![CDATA[<p>AI 부트캠프 참가 안내</p>]]></description>
    </item>
  </channel>
</rss>
""".strip().encode("utf-8")


def test_parse_notices_extracts_normalized_fields():
    notices, rejected = parse_notices(RSS_XML, "uos_general")

    assert rejected == []
    assert notices == [
        {
            "source": "uos_general",
            "source_id": "12345",
            "title": "테스트 일반공지",
            "description": "<p>AI 부트캠프 참가 안내</p>",
            "url": "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&seq=12345&sort=7",
            "published_at": "2026-11-04T12:30:00+09:00",
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

    with pytest.raises(ValueError, match="공지가 없습니다"):
        parse_notices(invalid_xml, "uos_general")


def test_parse_notices_rejects_feed_without_items():
    empty_feed = b"<rss><channel></channel></rss>"

    with pytest.raises(ValueError, match="공지 항목"):
        parse_notices(empty_feed, "uos_general")


def test_parse_notices_skips_invalid_item_and_keeps_others():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>정상 공지 1</title>
          <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&amp;seq=100</link>
          <pubDate>2026-11-04 10:00:00</pubDate>
        </item>
        <item>
          <title>seq 없는 공지</title>
          <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1</link>
          <pubDate>2026-11-04 11:00:00</pubDate>
        </item>
        <item>
          <title>정상 공지 2</title>
          <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&amp;seq=102</link>
          <pubDate>2026-11-04 12:00:00</pubDate>
        </item>
      </channel>
    </rss>""".encode("utf-8")

    notices, rejected = parse_notices(xml, "uos_general")

    # 정상 공지 2건만 남아야 한다
    assert [n["source_id"] for n in notices] == ["100", "102"]

    # 제외된 공지 1건이 이유와 함께 기록되어야 한다
    assert len(rejected) == 1
    assert rejected[0]["title"] == "seq 없는 공지"
    assert rejected[0]["url"] == "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1"
    assert rejected[0]["reason"]  # 이유 문자열이 비어 있지 않으면 통과

def test_parse_notices_skips_item_without_title():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>   </title>
      <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&amp;seq=200</link>
    </item>
    <item>
      <title>정상 공지</title>
      <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&amp;seq=201</link>
    </item>
  </channel>
</rss>""".encode("utf-8")

    notices, rejected = parse_notices(xml, "uos_general")

    assert [n["source_id"] for n in notices] == ["201"]
    assert len(rejected) == 1
    assert rejected[0]["reason"] == "공지 제목이 없습니다."

def test_parse_published_at_adds_korea_timezone():
    assert parse_published_at("2026-11-04 16:51:35") == "2026-11-04T16:51:35+09:00"


def test_parse_published_at_returns_none_for_invalid_date():
    assert parse_published_at("2026-13-40 99:00:00") is None


def test_parse_published_at_returns_none_for_missing_value():
    assert parse_published_at(None) is None
    assert parse_published_at("") is None


HAKSA_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>학사 공지</title>
      <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA2&amp;seq=9900</link>
      <pubDate>2026-11-06 10:00:00</pubDate>
    </item>
  </channel>
</rss>""".encode("utf-8")


def test_parse_notices_uses_source_settings():
    notices, rejected = parse_notices(HAKSA_XML, "uos_haksa")

    assert rejected == []
    assert notices[0]["source"] == "uos_haksa"
    assert notices[0]["source_id"] == "9900"


def test_parse_notices_rejects_item_from_other_board():
    # 학사공지(FA2) 글을 일반공지(FA1)로 파싱하면 제외되어야 함
    with pytest.raises(ValueError, match="공지가 없습니다"):
        parse_notices(HAKSA_XML, "uos_general")

