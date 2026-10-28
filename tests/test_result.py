import json

import jsonschema
import pytest

from grillepain.result import SCHEMA_PATH
from helpers import run_result

SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_valid(sample_result):
    d = sample_result.to_dict()
    jsonschema.validate(d, SCHEMA)
    json.dumps(d)  # pas de types numpy
    assert d["schema_version"] == "1.0.0" and d["accuracy"]["timing_ms"] == 20
    assert d["alignment"]["reliable"] is True and sample_result.warnings == []


def test_unreliable_warns(sample_result_faible):
    d = sample_result_faible.to_dict()
    assert d["alignment"]["reliable"] is False
    assert any("peu fiable" in w for w in sample_result_faible.warnings)
    jsonschema.validate(d, SCHEMA)


def test_write_json(sample_result, tmp_path):
    p = tmp_path / "r.json"
    sample_result.write_json(p)
    assert json.loads(p.read_text(encoding="utf-8")) == sample_result.to_dict()


def test_schema_rejects_string_midi(sample_result):
    d = sample_result.to_dict()
    d["notes"][0]["midi"] = "60"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, SCHEMA)


def test_schema_rejects_wrong_version(sample_result):
    d = sample_result.to_dict()
    d["schema_version"] = "2.0.0"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, SCHEMA)


@pytest.mark.parametrize("key,val", [("confidence", "super"), ("method_id", "autre")])
def test_schema_rejects_bad_enum(sample_result, key, val):
    d = sample_result.to_dict()
    d["alignment"][key] = val
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, SCHEMA)


def test_method_id_and_glossary_copy(sample_result):
    d = sample_result.to_dict()
    assert d["alignment"]["method_id"] in ("downbeat_arg", "count_in", "harmonic")
    d["glossary"]["x"] = "y"
    assert "x" not in sample_result.to_dict()["glossary"]


@pytest.mark.golden
def test_example_validates(example_mkv):
    jsonschema.validate(run_result(example_mkv).to_dict(), SCHEMA)
