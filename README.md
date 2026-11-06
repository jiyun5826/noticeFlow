# NoticeFlow

서울시립대학교 공지를 공식 RSS로 수집해, **관심 있는 새 공지만** Discord로 알려주는 자동화 도구입니다.
여러 게시판을 직접 반복 방문하며 새 공지를 골라내던 일을 대신하고, AWS EC2에서 n8n으로 매시 자동 실행됩니다.

## 하는 일

```text
n8n (매시 정각)
  └─ python -m src.main
       ├─ 출처별 RSS 수집 ── 일반공지, 학사공지 (한 출처가 실패해도 나머지는 계속)
       ├─ 검증·정규화 ───── 잘못된 항목만 제외, 게시일을 KST ISO 8601로
       ├─ 키워드 분류 ───── config/keywords.json (제목 + 본문)
       ├─ 알림 판단 ─────── 처음 저장될 때 한 번: 관심 공지 AND 게시일 3일 이내 → PENDING
       ├─ SQLite 저장 ───── UNIQUE(source, source_id)로 중복 제거
       ├─ Discord 발송 ──── PENDING·FAILED(3회 미만) 공지를 임베드 카드로
       └─ 실행 기록 ─────── collection_runs 테이블
  실패(종료 코드 ≠ 0) → n8n Error Trigger → Discord 실패 알림
```

## 현재 구현 범위

| 기능 | 상태 |
| --- | --- |
| 공식 RSS 수집 (일반공지 `gBoard.do`, 학사공지 `hBoard.do`) | 구현·테스트 완료, 운영 중 |
| 출처별 게시판 검증(`list_id`)과 게시글 ID(`seq`) 추출 | 구현·테스트 완료 |
| 잘못된 항목만 제외, 출처 하나가 실패해도 나머지 계속 | 구현·테스트 완료 |
| 게시일 KST ISO 8601 정규화 | 구현·테스트 완료 |
| SQLite 저장과 `(source, source_id)` 중복 제거 | 구현·테스트 완료 |
| 관심 키워드 분류와 알림 판단(최근 3일) | 구현·테스트 완료, 운영 중 |
| Discord 임베드 카드 발송, 실패 시 다음 실행에서 재시도(최대 3회) | 구현·테스트 완료, 운영 중 |
| 실행 기록(`collection_runs`) | 구현·테스트 완료, 운영 중 |
| 기존 DB에 없는 컬럼만 추가하는 마이그레이션 | 구현·테스트 완료, 운영 DB에 적용 |
| EC2 + n8n 매시 실행, 실패 알림, 매일 DB 백업 | 운영 중 (2026-11-05부터) |
| LLM 요약, Google Sheets, 학과 공지 | 미구현 (다음 개선) |

## 알림 정책

| 조건 | 결과 |
| --- | --- |
| 관심 키워드에 걸리지 않음 | 저장만 하고 알림 안 함 (`SKIPPED`) |
| 관심 공지 + 게시일이 3일 이내 | 알림 (`PENDING` → `SENT`) |
| 관심 공지 + 게시일이 3일보다 오래됨 | 저장만 함 (`SKIPPED`) |
| 관심 공지 + 게시일을 알 수 없음 | 알림 (놓치는 것보다 한 번 더 받는 편을 택함) |

**왜 "DB에 처음 들어온 공지"가 아니라 게시일로 판단하나요?**
학교 RSS는 한 번에 24건만 제공하고, 게시일이 아니라 **수정일 순서**로 정렬됩니다(학교 RSS 안내 페이지에 명시).
그래서 상단 고정 공지나 수정된 예전 공지가 RSS에 다시 나타나며, 실제로 한 번의 실행에서 "처음 저장된 14건 중 실제 새 게시물은 4건"이었습니다.
알림 여부는 공지가 **처음 저장될 때 한 번만** 정하고, 이후 다시 나타나도 `ON CONFLICT DO NOTHING`으로 기존 상태(`SENT` 등)를 유지합니다.
덕분에 DB를 새로 만들어 처음 실행해도 최근 관심 공지만 알림이 가고, 과거 공지가 한꺼번에 발송되지 않습니다.

## 실패 처리

| 실패 | 처리 |
| --- | --- |
| RSS 요청 실패(네트워크, HTTP 오류) | 해당 출처만 실패로 기록하고 다른 출처는 계속. 끝에 에러를 던져 n8n 실패 알림 |
| 응답 전체가 이상함(항목 0건, 유효한 공지 0건) | 해당 출처 실패 |
| 항목 일부가 이상함(제목 없음, 다른 게시판 링크) | 그 항목만 제외 |
| 게시일 형식 오류 | 공지는 저장, `published_at`만 `NULL` |
| Discord 발송 실패(4xx·5xx·타임아웃) | 그 공지만 `FAILED`, 시도 횟수·에러 기록, 다음 실행에서 재시도. 3회 실패하면 중단 |
| 환경변수 누락 | 실행 실패로 기록하고 n8n 실패 알림 |

- 발송 실패 시 **그 자리에서 바로 재시도하지 않습니다.** 클라이언트는 에러로 끝났지만 실제로는 전송된 경우를 확인한 적이 있어, 즉시 재시도하면 중복 알림이 생길 수 있기 때문입니다.
- 에러 메시지에는 웹훅 URL이 포함될 수 있어 `HTTP 상태코드` 또는 예외 이름만 저장합니다.
- 실행 상태: `SUCCESS` / `PARTIAL`(일부 출처 실패) / `FAILED`

## 운영 구성

| 항목 | 내용 |
| --- | --- |
| 서버 | AWS EC2 (서울, Ubuntu 24.04, t3.small, 12GiB gp3) |
| 실행 | n8n(systemd 서비스) Schedule Trigger → Execute Command `cd ~/noticeFlow && .venv/bin/python -m src.main` |
| 실패 알림 | n8n Error Trigger 워크플로 → Discord (웹훅 URL은 n8n Credential에 보관) |
| 백업 | n8n 매일 04:30 `sqlite3 .backup`, 7일 지난 백업 삭제 |
| 보안 | SSH는 지정 IP만 허용, n8n은 `127.0.0.1`에서만 수신하고 SSH 터널로 접속 |
| 비밀값 | 서버의 `.env`(권한 600)에만 보관, 저장소에는 `.env.example`만 포함 |

n8n은 실행 예약과 실패 감지만 맡고, 수집·중복 제거·알림 판단·재시도 로직은 테스트 가능한 Python에 둡니다.

### n8n 워크플로 파일

`n8n/` 폴더에 운영 중인 워크플로를 내보내 두었습니다. 웹훅 URL은 포함되지 않으며, Discord Credential은 ID와 이름만 들어 있습니다.

| 파일 | 내용 |
| --- | --- |
| `n8n/hourly.json` | 매시 정각 `python -m src.main` 실행, 실패 시 error alert 호출 |
| `n8n/error-alert.json` | Error Trigger → Discord로 실패한 워크플로·시각·오류 마지막 줄 전송 |
| `n8n/daily-backup.json` | 매일 04:30 SQLite 백업, 7일 지난 백업 삭제 |

다른 n8n에서 사용하려면:

1. n8n 실행 환경에서 Execute Command 노드를 사용할 수 있어야 합니다(필요하면 `NODES_EXCLUDE=[]`).
2. 워크플로 메뉴 → **Import...**로 세 파일을 가져옵니다.
3. `error-alert`의 Discord 노드에 자신의 웹훅 URL로 Credential을 새로 만듭니다.
4. `hourly`와 `daily-backup`의 Settings에서 Error Workflow를 가져온 `error-alert`로 다시 지정합니다(가져오면 ID가 바뀝니다).
5. Execute Command의 경로(`/home/ubuntu/noticeFlow`)를 실제 설치 경로로 바꾸고 Publish합니다.

## 설치

Windows PowerShell 기준입니다. Python 3.10 이상이 필요합니다(개발: Windows 3.13, 운영: Ubuntu 3.12).

```powershell
git clone https://github.com/jiyun5826/noticeFlow.git
cd noticeFlow
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
```

`.env`에 Discord 웹훅 URL을 넣습니다.

```text
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## 실행

```powershell
python -m src.main
```

`src` 패키지 경로로 import하므로 `python src/main.py`로는 실행되지 않습니다.
현재 폴더의 `noticeflow.db`를 만들거나 사용하며, 출력 예시는 다음과 같습니다.

```text
[일반] 수집 24 / 제외 0 / 신규 0
[학사] 수집 24 / 제외 0 / 신규 24
알림 발송: 2 / 실패: 0
실행시간: 3015ms
```

> 운영 DB가 따로 있다면 다른 곳에서 같은 웹훅으로 실행하지 마세요. 각 DB가 서로의 발송 기록을 모르기 때문에 중복 알림이 갑니다.

## 설정

| 파일 | 내용 |
| --- | --- |
| `.env` | `DISCORD_WEBHOOK_URL` |
| `config/keywords.json` | 관심 키워드 목록(`include`). 기관명에 포함돼 오탐이 많은 단어(예: `AI`, `교육`)는 제외 |
| `src/sources.py` | 출처 목록(이름, RSS 주소, 게시판 `list_id`). 키는 DB의 `source` 값이므로 기존 키는 바꾸지 않음 |

## 테스트

```powershell
python -m pytest -v
```

네트워크 없이 고정 XML(fixture), 임시 DB, 가짜 발송·수집 함수로 실행됩니다. 총 36개입니다.

| 파일 | 검증 내용 |
| --- | --- |
| `test_parser.py` | 필드 추출, 출처별 게시판 검증, 잘못된 항목만 제외, 빈 피드 거부, 게시일 정규화 |
| `test_db.py` | 중복 저장 방지, 기존 알림 상태 유지, 발송 대상 조회·재시도 한도, 실행 기록, 마이그레이션(기존 데이터 보존·멱등성) |
| `test_notify.py` | 알림 판단(3일 경계, 비관심, 날짜 없음), 출처별 카드 링크·footer, 긴 제목 자르기 |
| `test_classifier.py` | 키워드 매칭과 설정 로드 |
| `test_pipeline.py` | Discord 429·타임아웃 기록, 다음 실행 재시도, 출처 하나 실패 시 나머지 계속 |
| `test_experiments.py` | 통제 실험 A·B (아래) |

### 통제 실험 (fixture 기반)

```powershell
python -m pytest tests/test_experiments.py -v -s
```

| 실험 | 조건 | 결과 |
| --- | --- | --- |
| A. 중복 알림 | 동일 공지 100건을 3회 수집 | 신규 저장 100 → 0 → 0, 알림 100 → 0 → 0 |
| B. 신규 탐지 | 기존 100건 수집 후 기존 100 + 신규 20 수집 | 신규 저장 20, 알림 20, 누락 0, 오탐 0 |

실제 `collect_source`·`send_pending_notices`를 쓰되 RSS와 Discord만 가짜로 바꾼 통제 실험입니다. 실제 운영(24건 제한, 수정일 순 정렬)의 완전 탐지를 보장하지는 않습니다.

### 실제 환경에서 확인한 것

| 날짜 | 확인 |
| --- | --- |
| 11/4 | 실제 RSS 연속 2회 실행 시 신규 24 → 0 |
| 11/5 | Discord 웹훅 URL을 일부러 틀려 401 → 다음 실행에서 재시도 성공 → 이후 중복 없음 |
| 11/5 | 네트워크 차단 시 `FAILED`와 원인이 실행 기록에 남음 |
| 11/5 | 서버 환경변수를 숨긴 예약 실행 실패 → n8n이 Discord로 실패 알림 |
| 11/6 | 운영 DB 마이그레이션(백업 후 배포), 기존 데이터 유지 확인 |
| 11/6 | 학사공지 추가 배포, 카드 링크가 실제 학사공지 글로 열림 |

## 데이터 구조

**`notices`** (`UNIQUE(source, source_id)`)

| 컬럼 | 설명 |
| --- | --- |
| `source`, `source_id` | 출처 키(`uos_general`, `uos_haksa`)와 게시글 번호 |
| `title`, `url`, `published_at` | 제목, 링크, 게시일(KST 오프셋 포함 ISO 8601, 확인 불가 시 NULL) |
| `first_seen_at` | 최초 수집 시각(UTC) |
| `is_relevant`, `matched_keywords` | 관심 여부, 걸린 키워드 |
| `notify_status` | `PENDING` / `SKIPPED` / `SENT` / `FAILED` |
| `notify_attempts`, `notify_last_error`, `notified_at` | 발송 시도 횟수, 마지막 에러, 발송 시각 |

**`collection_runs`**: 실행 시각, 상태, 수집·제외·신규 건수, 발송 성공·실패 건수, 소요 시간, 에러

## 알려진 한계

- 학교 RSS는 한 번에 24건, 수정일 순입니다. 실행 간격 동안 그보다 많은 공지가 올라오면 누락될 수 있습니다. 실측상 일반공지 새 게시물은 하루 약 5건이라 1시간 간격으로 실행합니다.
- 학과 공지는 공식 RSS가 없어 수집하지 않습니다. 목록 페이지는 학교 SSO 흐름을 거치므로 사용하지 않았습니다.
- 키워드 규칙은 맥락을 모릅니다. 예: "[교직] 산업체현장실습"이 `현장실습`으로 매칭됨. 기관명에 들어간 단어(`AI` 등)는 키워드로 쓰기 어렵습니다.
- Discord 응답이 유실되면 같은 공지가 다시 발송될 수 있습니다(정확히 한 번 전송은 보장하지 않음).
- 백업은 같은 서버 디스크에 있어 서버 자체가 사라지면 함께 사라집니다.
- n8n을 컨테이너 밖에서 실행 중이며, 향후 n8n 버전은 Docker 실행을 요구할 예정입니다.
- `first_seen_at`(UTC, 표기 없음)과 `published_at`(KST 오프셋 포함)의 표기 방식이 다릅니다.

## 다음 개선

- LLM으로 공지 요약·마감일 추출, 키워드 규칙과 정확도 비교
- 마감일 트래커(Google Sheets)
- 학과 공지(HTML 수집 가능성 검토)
- 백업 파일 S3 복사, n8n Docker 전환

## 프로젝트 구조

```text
config/keywords.json   관심 키워드
src/main.py            수집·파싱·정규화, 출처별 수집(collect_all), 발송(send_pending_notices), 실행 진입점
src/sources.py         출처 목록
src/db.py              SQLite 스키마, 마이그레이션, 저장·조회
src/notify.py          알림 판단, Discord 카드 생성·발송
src/classifier.py      키워드 분류
n8n/                   n8n 워크플로 내보내기(JSON)
tests/                 pytest 테스트와 통제 실험
```
