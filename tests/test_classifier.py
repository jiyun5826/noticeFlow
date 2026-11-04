from src.classifier import find_matching_keywords, load_keywords
from src.classifier import (
    classify_notice,
    find_matching_keywords,
    load_keywords,
)

def test_find_matching_keywords_returns_only_matches():
    keywords = ["공모전", "대회", "부트캠프"]

    assert find_matching_keywords(
        "AI 공모전 및 부트캠프 참가자 모집",
        keywords,
    ) == ["공모전", "부트캠프"]

    assert find_matching_keywords(
        "2026학년도 장학금 신청 안내",
        keywords,
    ) == []

def test_load_keywords_reads_include_list(tmp_path):
    config_path = tmp_path / "keywords.json"
    config_path.write_text(
        '{"include": ["공모전", "대회"]}',
        encoding="utf-8",
    )

    assert load_keywords(config_path) == ["공모전", "대회"]

def test_classify_notice_uses_title_and_description():
    notice = {
        "title": "AI 프로그램 참가자 모집",
        "description": "<p>대학생 대상 부트캠프입니다.</p>",
    }

    classified = classify_notice(
        notice,
        ["공모전", "대회", "부트캠프"],
    )

    assert classified["is_relevant"] is True
    assert classified["matched_keywords"] == ["부트캠프"]