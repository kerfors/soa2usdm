"""
Test identity page (soa2usdm.test_identity_page, step 6a-2): every published test identity file renders,
the summary lists every level with counts that add up, the page refuses a stale file and an unknown level,
and the badges keep to the two hooks in the data.
"""
import copy
import json
import re

import pytest

from soa2usdm import config
from soa2usdm import test_identity_page as tp


def _published():
    out = []
    for coll in [c for c in config.COLLECTIONS if c != "fixtures"]:
        out += [(coll, p.name.split("_test_identity")[0])
                for p in sorted(config.COLLECTIONS[coll].glob("*/SoA2USDM/test_identity/*_test_identity.json"))]
    return out


@pytest.mark.parametrize("coll, pid", _published(), ids=lambda x: x)
def test_published_pages_render(coll, pid):
    html = tp.build_html(pid, coll)
    d = json.loads(tp.test_identity_path(pid, coll).read_text(encoding="utf-8"))
    for level in tp.LEVELS:
        assert f">{level}</span>" in html
    rows = [r for r in d["rows"] if r["unit"] != "activity"]
    assert len(re.findall(r'<tr id="[^"]+" data-l="[^"]', html)) == len(rows)
    for r in d["rows"]:
        rid = r["xact_id"] + (f'.{r["member_id"]}' if "member_id" in r else "")
        assert f'id="{rid}"' in html and f'_activity_routing.html#{rid}"' in html
    assert "test identity" in html and "pnav" in html
    c = tp.index_counts(d)
    assert c["standalone"][1] + c["member"][1] == len(rows)


def test_stale_file_is_refused(tmp_path, monkeypatch):
    coll, pid = _published()[0]
    src = tp.test_identity_path(pid, coll)
    d = json.loads(src.read_text(encoding="utf-8"))
    d["inputs"]["activity_routing"]["sha256"] = "0" * 64
    fake = tmp_path / pid / "SoA2USDM" / "test_identity" / src.name
    fake.parent.mkdir(parents=True)
    fake.write_text(json.dumps(d), encoding="utf-8")
    (tmp_path / pid / "SoA2USDM" / "routing").mkdir()
    routing = src.parent.parent / "routing" / f"{pid}_activity_routing.json"
    (tmp_path / pid / "SoA2USDM" / "routing" / routing.name).write_bytes(routing.read_bytes())
    monkeypatch.setattr(tp, "test_identity_path", lambda p, c: fake)
    with pytest.raises(RuntimeError, match="stale"):
        tp.build_html(pid, coll)


def test_unknown_level_fails():
    coll, pid = _published()[0]
    d = json.loads(tp.test_identity_path(pid, coll).read_text(encoding="utf-8"))
    d = copy.deepcopy(d)
    r = next(r for r in d["rows"] if r["unit"] != "activity")
    r["specialization"]["level"] = "a level nobody wrote"
    with pytest.raises(ValueError, match="unknown"):
        tp._summary(d)


def test_badges_only_from_hooks_in_the_data():
    base = {"facets": [], "specialization": {"level": "one specialization"}}
    assert tp._badges(base) == []
    gh = base | {"group_head": {"member_id": "c01", "text": "dipstick", "read": False}}
    assert tp._badges(gh) == []   # shown in the group header, not badged
    serum = {"facets": [{"position": "system", "term": {"concept_id": "C13325"}}],
             "specialization": {"level": "stated facet matches no specialization"}}
    assert tp._badges(serum) == ["SERUM or PLASMA against SERUM OR PLASMA"]
    urine = {"facets": [{"position": "system", "term": {"concept_id": "C13283"}}],
             "specialization": {"level": "stated facet matches no specialization"}}
    assert tp._badges(urine) == []
