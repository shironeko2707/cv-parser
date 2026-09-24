"""
Maps extracted free-text values to picklist optionIds using fuzzy matching.
Handles both Vietnamese and English labels.
"""
from rapidfuzz import fuzz, process
from schema_loader import Schema, PicklistValue


ABBREVIATION_EXPANSIONS: dict[str, list[str]] = {
    "tp hcm": ["ho chi minh", "hồ chí minh"],
    "tp. hcm": ["ho chi minh", "hồ chí minh"],
    "tphcm": ["ho chi minh", "hồ chí minh"],
    "hn": ["ha noi", "hà nội"],
    "tp. hn": ["ha noi", "hà nội"],
    "sg": ["ho chi minh"],
    "mba": ["master", "master of business administration"],
    "cu nhan": ["cử nhân", "bachelor"],
    "thac si": ["thạc sĩ", "master"],
    "tien si": ["tiến sĩ", "phd"],
    "ky su": ["kỹ sư", "engineer"],
    "cccd": ["căn cước công dân", "people identification card"],
    "cmnd": ["chứng minh nhân dân", "people identification card"],
    "cmtnd": ["chứng minh nhân dân", "people identification card"],
}


from text_utils import strip_diacritics as _strip_diacritics


class PicklistMapper:
    def __init__(self, schema: Schema):
        self.schema = schema
        self._indexes: dict[str, dict[str, PicklistValue]] = {}
        self._choices: dict[str, list[str]] = {}

        for pid, values in schema.picklists.items():
            index: dict[str, PicklistValue] = {}
            choices: list[str] = []
            for v in values:
                if v.status != "A":
                    continue
                for label in [v.label_en, v.label_vi, v.external_code]:
                    if label and label.lower() != "nodata":
                        key = label.lower().strip()
                        index[key] = v
                        # Also index without diacritics
                        key_ascii = _strip_diacritics(label)
                        index[key_ascii] = v
                        choices.append(label)
            self._indexes[pid] = index
            self._choices[pid] = choices

    def match(self, picklist_id: str, text: str, threshold: int = 70) -> PicklistValue | None:
        if not text or picklist_id not in self._indexes:
            return None

        text_lower = text.lower().strip()
        text_ascii = _strip_diacritics(text)
        index = self._indexes[picklist_id]

        # Exact match first (with and without diacritics)
        if text_lower in index:
            return index[text_lower]
        if text_ascii in index:
            return index[text_ascii]

        # Abbreviation expansion
        for abbrev, expansions in ABBREVIATION_EXPANSIONS.items():
            if text_lower == abbrev or text_ascii == abbrev:
                for exp in expansions:
                    if exp.lower() in index:
                        return index[exp.lower()]
                    exp_ascii = _strip_diacritics(exp)
                    if exp_ascii in index:
                        return index[exp_ascii]

        # Fuzzy match
        choices = self._choices.get(picklist_id, [])
        if not choices:
            return None

        results = process.extract(text, choices, scorer=fuzz.WRatio, limit=3)
        if results and results[0][1] >= threshold:
            best_label = results[0][0].lower().strip()
            return index.get(best_label)

        return None

    def match_id(self, picklist_id: str, text: str, threshold: int = 70) -> str | None:
        """Returns just the optionId string, or None."""
        result = self.match(picklist_id, text, threshold)
        return result.option_id if result else None


if __name__ == "__main__":
    from schema_loader import load_schema

    schema = load_schema()
    mapper = PicklistMapper(schema)

    tests = [
        ("salutation", "Ms."),
        ("salutation", "Bà"),
        ("salutation", "Mr"),
        ("cptCityProvince", "Ha Noi"),
        ("cptCityProvince", "Hà Nội"),
        ("cptCityProvince", "TP HCM"),
        ("cptCityProvince", "Ho Chi Minh"),
        ("eduDegree", "Bachelor"),
        ("eduDegree", "Cử nhân"),
        ("eduDegree", "MBA"),
        ("eduDegree", "Thạc sĩ"),
        ("language", "English"),
        ("language", "Tiếng Anh"),
        ("fluency", "Fluent"),
        ("fluency", "Intermediate"),
        ("fluency", "Trung cấp"),
        ("country", "VN"),
        ("country", "Vietnam"),
        ("ISOCountryList", "Vietnam"),
        ("nationalIDCardType", "CCCD"),
        ("nationalIDCardType", "Hộ chiếu"),
        ("university", "Đại học Bách Khoa Hà Nội"),
        ("major", "Computer Science"),
    ]

    for pid, text in tests:
        result = mapper.match(pid, text)
        if result:
            print(f"  {pid} + '{text}' -> id={result.option_id} ({result.label_en})")
        else:
            print(f"  {pid} + '{text}' -> NO MATCH")
