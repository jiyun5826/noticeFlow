import json
from pathlib import Path
def find_matching_keywords(text: str, keywords: list[str]) -> list[str]:
    normalized_text = text.casefold()

    return [
        keyword
        for keyword in keywords
        if keyword.strip() and keyword.casefold() in normalized_text
    ]

def load_keywords(config_path: str | Path) -> list[str]:
    with Path(config_path).open(encoding="utf-8") as file:
        config = json.load(file)

    keywords = config.get("include")

    if not isinstance(keywords, list) or not all(
        isinstance(keyword, str) for keyword in keywords
    ):
        raise ValueError("키워드 설정의 include는 문자열 목록이어야 합니다.")

    return keywords