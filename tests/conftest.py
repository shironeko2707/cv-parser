import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from schema_loader import FieldDef, PicklistValue, Schema  # noqa: E402


def _f(fid, ftype="String", picklist=None, section=None, nested=None, label=""):
    return FieldDef(fid, ftype, label or fid, picklist, False, "", "", section, nested)


@pytest.fixture
def fake_schema() -> Schema:
    """A small stand-in for the (private) SuccessFactors Excel schema."""
    top = [
        _f("firstName"), _f("middleName"), _f("lastName"), _f("primaryEmail"), _f("contactEmail"),
        _f("cellPhone"), _f("dateOfBirth", "DateTime"), _f("address"),
        _f("country", "Picklist", "ISOCountryList"), _f("gender", "Picklist", "gender"),
        _f("custBirthPlace", label="Nơi sinh / Place of birth"),
    ]
    edu = [_f(f"education.results.{k}", t, pl, "education", k) for k, t, pl in [
        ("school", "Picklist", "university"), ("otherSchool", "String", None), ("degree", "String", None),
        ("startDate", "DateTime", None), ("endDate", "DateTime", None)]]
    exp = [_f(f"outsideWorkExperience.results.{k}", t, None, "outsideWorkExperience", k) for k, t in [
        ("startTitle", "String"), ("employer", "String"), ("startDate", "DateTime"),
        ("endDate", "DateTime"), ("description", "String")]]
    lang = [_f(f"languages.results.{k}", "String", None, "languages", k) for k in ("language", "fluency")]
    fam = [_f(f"familyMember.results.{k}", "String", None, "familyMember", k)
           for k in ("firstName", "middleName", "lastName", "relationship")]
    sections = {"education": edu, "outsideWorkExperience": exp, "languages": lang, "familyMember": fam}
    picklists = {
        "university": [PicklistValue("HUST", "Đại học Bách khoa Hà Nội", "Hanoi University of Science and Technology", "501", "A")],
        "ISOCountryList": [PicklistValue("VN", "Việt Nam", "Vietnam", "704", "A")],
        "gender": [PicklistValue("M", "Nam", "Male", "1", "A"), PicklistValue("F", "Nữ", "Female", "2", "A")],
    }
    return Schema(fields=top + [f for v in sections.values() for f in v], picklists=picklists,
                  top_level_fields=top, sections=sections)
