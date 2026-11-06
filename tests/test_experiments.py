from datetime import datetime, timedelta, timezone

import src.main as main
from src.db import init_db

KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=KST)


def _rss(seqs):
    items = "".join(
        f"""
    <item>
      <title>인턴 모집 {seq}</title>
      <link>https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&amp;seq={seq}</link>
      <pubDate>2026-11-06 10:00:00</pubDate>
    </item>"""
        for seq in seqs
    )
    return f'<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>{items}</channel></rss>'.encode("utf-8")


class _FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def _run(monkeypatch, db_path, seqs):
    xml = _rss(seqs)
    monkeypatch.setattr(main.requests, "get", lambda *args, **kwargs: _FakeResponse(xml))

    result = main.collect_source(db_path, "uos_general", ["인턴"], NOW)

    sent_seqs = []
    def sender(webhook_url, payload):
        sent_seqs.append(payload["embeds"][0]["url"].split("seq=")[1])

    main.send_pending_notices(db_path, "fake", sender=sender, sleep=lambda s: None)
    return result["inserted"], sent_seqs


def test_experiment_a_same_100_notices_three_times(tmp_path, monkeypatch):
    db_path = str(tmp_path / "exp_a.db")
    init_db(db_path)
    seqs = [str(n) for n in range(1, 101)]

    runs = [_run(monkeypatch, db_path, seqs) for _ in range(3)]

    inserted = [r[0] for r in runs]
    sent = [len(r[1]) for r in runs]
    print(f"\n[실험 A] 신규 저장 {inserted}, 알림 {sent}")
    assert inserted == [100, 0, 0]
    assert sent == [100, 0, 0]


def test_experiment_b_detects_exactly_20_new_notices(tmp_path, monkeypatch):
    db_path = str(tmp_path / "exp_b.db")
    init_db(db_path)
    old = [str(n) for n in range(1, 101)]
    new = [str(n) for n in range(101, 121)]

    _run(monkeypatch, db_path, old)
    inserted, sent = _run(monkeypatch, db_path, old + new)

    missed = set(new) - set(sent)
    wrong = set(sent) - set(new)
    print(f"\n[실험 B] 신규 저장 {inserted}, 알림 {len(sent)}, 누락 {len(missed)}, 오탐 {len(wrong)}")
    assert inserted == 20
    assert missed == set()
    assert wrong == set()