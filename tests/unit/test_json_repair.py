import pytest

from pipeline.llm.json_repair import JSONRepairError, parse_json, strip_reasoning


def test_plain_object():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_think_block_removed():
    assert parse_json('<think>let me reason {"no": 1}</think>\n{"a": 2}') == {"a": 2}


def test_unterminated_think_means_no_answer():
    with pytest.raises(JSONRepairError):
        parse_json('<think>still reasoning {"a": 1}')


def test_code_fence():
    assert parse_json('Here you go:\n```json\n{"cards": [1, 2]}\n```\nDone.') == {"cards": [1, 2]}


def test_prose_around_json():
    assert parse_json('Sure! The result is {"a": [1, {"b": "x}y"}]} hope that helps') == {"a": [1, {"b": "x}y"}]}


def test_trailing_commas():
    assert parse_json('{"a": [1, 2,], "b": {"c": 3,},}') == {"a": [1, 2], "b": {"c": 3}}


def test_comma_inside_string_untouched():
    assert parse_json('{"a": "x,}", "b": 1,}') == {"a": "x,}", "b": 1}


def test_truncated_nested():
    assert parse_json('{"a": {"x": 1, "y": [1, 2') == {"a": {"x": 1, "y": [1, 2]}}


def test_truncated_mid_string_value():
    assert parse_json('{"a": 1, "b": "hello wor') == {"a": 1, "b": "hello wor"}


def test_truncated_mid_key_drops_incomplete_member():
    assert parse_json('{"a": 1, "b') == {"a": 1}


def test_truncated_after_colon():
    assert parse_json('{"a": 1, "b":') in ({"a": 1, "b": None}, {"a": 1})


def test_truncated_array_of_objects_keeps_complete_items():
    out = parse_json('[{"h": "one"}, {"h": "two"}, {"h": "thr')
    assert out[:2] == [{"h": "one"}, {"h": "two"}]


def test_escaped_quotes():
    assert parse_json(r'{"q": "he said \"hi\""}') == {"q": 'he said "hi"'}


def test_expect_object_rejects_array():
    with pytest.raises(JSONRepairError, match="expected a JSON object"):
        parse_json("[1, 2]", expect="object")


def test_expect_array():
    assert parse_json("[1]", expect="array") == [1]


@pytest.mark.parametrize("bad", ["", "   ", "no json here", "<think>x</think>"])
def test_unrecoverable_raises(bad):
    with pytest.raises(JSONRepairError):
        parse_json(bad)


def test_strip_reasoning_keeps_answer():
    assert strip_reasoning("<THINK>a</THINK> answer") == "answer"
