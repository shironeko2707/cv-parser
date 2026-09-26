from json_assembler import assemble_json
from picklist_mapper import PicklistMapper
from schema_mapping import map_canonical, report, split_name

CANONICAL = {
    "personal": {"full_name": "NGUYỄN VĂN AN", "email": "an@x.vn", "phone": "0912 345 678",
                 "date_of_birth": "1995-03-15", "country": "Việt Nam", "gender": "male",
                 "place_of_birth": "Hà Nội", "linkedin": "linkedin.com/in/an"},
    "education": [
        {"institution": "Đại học Bách khoa Hà Nội", "degree": "Kỹ sư", "start_date": "2013", "end_date": "2018"},
        {"institution": "Some Unknown College", "degree": "MBA", "end_date": "2021-06"},
    ],
    "experience": [{"job_title": "Lập trình viên", "company": "FPT", "start_date": "2020-01",
                    "end_date": "present", "description": "a\nb"}],
    "languages": [{"language": "Tiếng Anh", "proficiency": "IELTS 7.0"}],
    "family": [{"full_name": "Nguyễn Văn Bình", "relationship": "Bố"}],
}


def test_split_name():
    assert split_name("NGUYỄN VĂN AN") == ("Nguyễn Văn An", "Nguyễn", "Văn", "An")
    assert split_name("Dr. Sarah Morgan") == ("Sarah Morgan", "Sarah", "", "Morgan")


def test_map_and_assemble(fake_schema):
    mapper = PicklistMapper(fake_schema)
    fields = map_canonical(CANONICAL, fake_schema, mapper)
    assert fields.personal["firstName"] == "Nguyễn" and fields.personal["lastName"] == "An"
    assert fields.personal["primaryEmail"] == fields.personal["contactEmail"] == "an@x.vn"
    assert fields.personal["custBirthPlace"] == "Hà Nội"  # resolved through the schema label
    assert "linkedin" not in str(fields.personal)          # not in this schema -> dropped
    assert fields.education[0]["school"] == "Đại học Bách khoa Hà Nội"  # picklist match
    assert fields.education[1]["otherSchool"] == "Some Unknown College"  # falls back to free text
    assert fields.family[0] == {"firstName": "Nguyễn", "middleName": "Văn", "lastName": "Bình",
                                "relationship": "Bố"}

    candidate = assemble_json(fields, fake_schema, mapper)[0]
    assert candidate["country"] == {"id": "704"}
    assert candidate["gender"] == {"id": "1"}
    assert candidate["dateOfBirth"] == "/Date(795225600000)/"
    edu = candidate["education"]["results"]
    assert edu[0]["school"] == "501" and edu[1]["endDate"] == "/Date(1622505600000)/"
    exp = candidate["outsideWorkExperience"]["results"][0]
    assert exp["endDate"] == "/Date(253402214400000)/" and exp["startTitle"] == "Lập trình viên"
    assert candidate["languages"]["results"][0] == {"language": "Tiếng Anh", "fluency": "IELTS 7.0"}


def test_report_lists_unmapped(fake_schema):
    text = report(fake_schema)
    assert "date_of_birth    -> dateOfBirth" in text
    assert "(not in schema)" in text
