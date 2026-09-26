import json

from ai_extractor import parse_llm_json
from canonical import (
    coerce, find_hints, ground, json_schema, merge_canonical, restrict_to_text, split_for_llm,
)
from date_normalizer import parse_date_parts, to_date_string, to_iso
from sections import match_section

CV = """NGUYỄN VĂN AN
an.nguyen@gmail.com | 0912 345 678 | linkedin.com/in/annguyen

## KINH NGHIỆM LÀM VIỆC
Công ty FPT Software | 01/2020 - nay
Lập trình viên
• Phát triển API cho hệ thống thanh toán

## HỌC VẤN
Đại học Bách khoa Hà Nội | 2015 - 2019
Kỹ sư Công nghệ thông tin"""


def test_ground_drops_hallucinations_and_repairs():
    pred = {
        "personal": {"full_name": "NGUYỄN VĂN AN", "email": "an.nguyen@gmail.con", "date_of_birth": "1995-01-01"},
        "experience": [
            {"job_title": "Lập trình viên", "company": "Công ty FPT Software", "start_date": "2020-01",
             "end_date": "present", "description": "Phát triển API cho hệ thống thanh toán"},
            {"job_title": "CTO", "company": "Google", "start_date": "2012"},
        ],
    }
    clean, conf = ground(pred, CV, find_hints(CV))
    assert clean["personal"]["email"] == "an.nguyen@gmail.com"  # repaired from regex hint
    assert clean["personal"]["phone"] == "0912 345 678"          # filled from hint
    assert clean["personal"]["linkedin"] == "linkedin.com/in/annguyen"
    assert "date_of_birth" not in clean["personal"]             # year not in text
    assert [e["company"] for e in clean["experience"]] == ["Công ty FPT Software"]
    assert conf["experience[1].company"] < 0.75


def test_coerce_handles_aliases_and_junk():
    out = coerce({"personal_info": {"full_name": "A B", "age": 3}, "work_experience": [
        {"company": "X", "description": ["a", "b"]}, "junk"], "skills": ["x"]})
    assert out == {"personal": {"full_name": "A B"}, "experience": [{"company": "X", "description": "a\nb"}]}


def test_split_and_merge_long_cv():
    long_cv = CV + "\n\n## CHỨNG CHỈ\n" + "\n".join(f"• Chứng chỉ số {i}" for i in range(400))
    chunks = split_for_llm(long_cv, 2000)
    assert len(chunks) > 1 and all(len(c) <= 2000 for c in chunks)
    assert chunks[0].startswith("NGUYỄN VĂN AN")
    assert all(c.startswith("## CHỨNG CHỈ") for c in chunks[1:])  # heading repeated for context
    merged = merge_canonical([
        {"personal": {"full_name": "A"}, "certificates": [{"name": "X"}]},
        {"personal": {"full_name": "B", "email": "e@x.vn"}, "certificates": [{"name": "X", "date": "2020"}, {"name": "Y"}]},
    ])
    assert merged["personal"] == {"full_name": "A", "email": "e@x.vn"}
    assert merged["certificates"] == [{"name": "X", "date": "2020"}, {"name": "Y"}]


def test_restrict_to_text_for_chunks():
    gold = {"personal": {"full_name": "NGUYỄN VĂN AN"},
            "education": [{"institution": "Đại học Bách khoa Hà Nội", "end_date": "2019"}],
            "experience": [{"company": "Công ty FPT Software", "job_title": "Lập trình viên"}]}
    part = restrict_to_text(gold, CV.split("## HỌC VẤN")[0])
    assert "education" not in part and part["experience"][0]["company"] == "Công ty FPT Software"


def test_parse_llm_json_repairs_truncation_and_fences():
    assert parse_llm_json('```json\n{"personal": {"full_name": "A"},}\n```') == {"personal": {"full_name": "A"}}
    truncated = '{"personal":{"full_name":"A"},"experience":[{"company":"X","description":"did thi'
    assert parse_llm_json(truncated)["experience"][0]["company"] == "X"


def test_json_schema_shape():
    s = json_schema()
    assert s["properties"]["personal"]["properties"]["gender"]["enum"] == ["male", "female", "other"]
    assert s["properties"]["experience"]["items"]["additionalProperties"] is False
    json.dumps(s)


def test_dates():
    assert to_iso("T3/2020") == "2020-03"
    assert to_iso("Tháng 12/2019") == "2019-12"
    assert to_iso("ngày 5 tháng 7 năm 1998") == "1998-07-05"
    assert to_iso("15/03/1995") == "1995-03-15"
    assert to_iso("12/25/2020") == "2020-12-25"   # day-first impossible -> month-first
    assert to_iso("Sep 2020") == "2020-09"
    assert to_iso("Đến nay") == "present"
    assert parse_date_parts("2020") == (2020, None, None)
    assert parse_date_parts("banana") is None
    assert to_date_string("2020-03") == "/Date(1583020800000)/"
    assert to_date_string("present", default_ongoing=True) == "/Date(253402214400000)/"


def test_section_headings():
    assert match_section("HỌC VẤN / EDUCATION") == "education"
    assert match_section("1. Kinh nghiệm làm việc:") == "experience"
    assert match_section("Skills & Tools") == "skills"
    assert match_section("BERUFSERFAHRUNG") == "experience"
    assert match_section("Head of Education") is None
    assert match_section("EDUCATION & MILITARY TRAINING", loose=True) == "education"
    assert match_section("Senior Software Engineer at a large company in Hanoi") is None
