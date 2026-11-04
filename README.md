# NoticeFlow

서울시립대학교 일반공지를 공식 RSS로 수집해 SQLite에 중복 없이 저장하는 Python 자동화 도구입니다.
게시판을 직접 반복 방문하며 새 공지를 골라내던 일을 자동화하는 것이 목표입니다.

> 개발 진행 중(2026-11)입니다. 아래 "현재 구현 범위"에 적힌 것만 동작합니다.

## 현재 구현 범위

| 기능 | 상태 |
| --- | --- |
| 공식 RSS(`https://www.uos.ac.kr/rss/gBoard.do`) 수집 | 구현·테스트 완료 |
| 일반공지 링크 검증(`list_id=FA1`) 및 게시글 ID(`seq`) 추출 | 구현·테스트 완료 |
| 잘못된 항목만 제외하고 나머지 처리 | 구현·테스트 완료 |
| 게시일을 KST 오프셋이 붙은 ISO 8601로 정규화 | 구현·테스트 완료 |
| SQLite 저장 및 `(source, source_id)` 기준 중복 제거 | 구현·테스트 완료 |
| 실행 시간 측정(콘솔 출력) | 구현 |
| 키워드 분류(`config/keywords.json`) | 함수·테스트만 구현, 수집 흐름에는 아직 미연결 |
| Google Sheets 기록, Slack 알림, 정기 실행(n8n) | 계획 |

## 요구 사항

- Python 3.10 이상 (개발 환경: Windows, Python 3.13)

## 설치

Windows PowerShell 기준입니다.

```powershell
git clone https://github.com/jiyun5826/noticeFlow.git
cd noticeFlow
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

실행만 할 때는 `requirements.txt`, 테스트까지 할 때는 `requirements-dev.txt`(pytest 포함)를 설치합니다.

## 실행

프로젝트 루트에서 실행합니다.

```powershell
python -m src.main
```

`src` 패키지 경로로 import하므로 `python src/main.py`로는 실행되지 않습니다.

실행하면 현재 폴더에 `noticeflow.db`가 생성(또는 재사용)되고 다음 정보가 출력됩니다.

```text
수집 건수: 24
제외 건수: 0
신규 저장 건수: 0
실행시간: 0.522초
```

- 수집 건수: RSS에서 읽은 항목 중 유효한 공지 수
- 제외 건수: 제목이 없거나 일반공지 링크 형식이 아니어서 제외한 항목 수
- 신규 저장 건수: DB에 처음 저장된 공지 수 (이미 있던 공지는 저장하지 않음)

## 테스트

```powershell
python -m pytest -v
```

테스트는 네트워크 없이 고정된 XML(fixture)과 임시 DB로 실행됩니다.

| 파일 | 검증 내용 |
| --- | --- |
| `tests/test_parser.py` | 필드 추출, 다른 게시판 링크 제외, 항목 0건 피드 거부, 잘못된 항목만 제외, 공백 제목 제외, 게시일 정규화(정상·잘못된 형식·빈 값) |
| `tests/test_db.py` | 같은 공지를 두 번 저장해도 한 번만 저장됨 |
| `tests/test_classifier.py` | 키워드 매칭, 설정 파일 로드, 제목+본문 기반 분류 |

## 동작 방식

1. RSS 요청 (타임아웃 10초, HTTP 오류 시 실패)
2. `channel/item` 파싱
3. 항목 검증
   - 제목이 비어 있거나 링크가 일반공지(`list_id=FA1`, `seq` 존재) 형식이 아니면 해당 항목만 제외
   - 항목이 0건이거나 유효한 항목이 0건이면 응답 전체를 신뢰할 수 없다고 보고 실행 실패
4. 게시일(`pubDate`)을 `2026-11-04T16:51:35+09:00` 형식으로 정규화. 형식이 잘못되면 값을 만들어내지 않고 `NULL`로 저장
5. SQLite에 `INSERT ... ON CONFLICT(source, source_id) DO NOTHING`으로 저장. 중복 판정은 애플리케이션의 사전 조회가 아니라 DB 고유 제약이 담당

### 저장 스키마 (`notices`)

| 컬럼 | 설명 |
| --- | --- |
| `source` | 수집처 (`uos_general`) |
| `source_id` | 게시글 번호(`seq`) |
| `title` | 제목 |
| `url` | 게시글 링크 |
| `published_at` | 게시일 (KST 오프셋 포함 ISO 8601, 확인 불가 시 NULL) |
| `first_seen_at` | 최초 수집 시각 (SQLite `CURRENT_TIMESTAMP`, UTC) |

`UNIQUE (source, source_id)`

## 알려진 한계

- RSS에는 최신 공지뿐 아니라 상단 고정 공지 등 오래된 공지도 섞여 들어오며, 구성이 시간에 따라 바뀝니다. 따라서 "DB에 처음 저장된 공지"가 "새로 게시된 공지"와 같지 않습니다. 알림 기능은 게시일 기준으로 판단하도록 설계할 예정입니다.
- `first_seen_at`은 시간대 표기 없는 UTC, `published_at`은 KST 오프셋 포함 형식으로 표기 방식이 다릅니다.
- 제외된 항목의 상세 내용과 실행 결과는 아직 콘솔에만 출력되며 파일·DB에 남지 않습니다.
- 서울시립대 일반공지 한 게시판만 지원합니다.

## 프로젝트 구조

```text
config/keywords.json   분류 키워드 설정
src/main.py            RSS 수집·파싱·정규화, 실행 진입점
src/db.py              SQLite 스키마와 저장
src/classifier.py      키워드 분류
tests/                 pytest 테스트
```
