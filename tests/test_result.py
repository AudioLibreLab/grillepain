import json

import jsonschema

from grillepain.result import SCHEMA_PATH


def test_schema_valid(sample_result):
    d = sample_result.to_dict()
    jsonschema.validate(d, json.load(open(SCHEMA_PATH)))
    json.dumps(d)  # pas de types numpy
    assert d["schema_version"] == "1.0.0" and d["accuracy"]["timing_ms"] == 20
    assert d["alignment"]["reliable"] is True and sample_result.warnings == []


def test_unreliable_warns(sample_result_faible):
    d = sample_result_faible.to_dict()
    assert d["alignment"]["reliable"] is False
    assert any("peu fiable" in w for w in sample_result_faible.warnings)
    jsonschema.validate(d, json.load(open(SCHEMA_PATH)))


def test_write_json(sample_result, tmp_path):
    p = tmp_path / "r.json"
    sample_result.write_json(p)
    assert json.loads(p.read_text(encoding="utf-8")) == sample_result.to_dict()
