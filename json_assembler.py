"""
Assembles extracted fields into the target JSON format,
applying picklist resolution and date normalization.
"""
import json
from schema_loader import Schema, FieldDef
from field_extractor import ExtractedFields
from picklist_mapper import PicklistMapper
from date_normalizer import to_date_string


DEFAULTS = {
    "anonymized": "0",
    "shareProfile": "1",
    "agreeToPrivacyStatement": "true",
}

SECTION_DATA_MAP = {
    "education": "education",
    "outsideWorkExperience": "experience",
    "languages": "languages",
    "certificates": "certificates",
    "awards": "awards",
    "courses": "courses",
    "familyMember": "family",
    "Disciplinary": "disciplinary",
}


def assemble_json(fields: ExtractedFields, schema: Schema, mapper: PicklistMapper) -> list[dict]:
    """Build the final JSON structure from extracted fields, following Excel schema order."""
    candidate: dict = {
        "__metadata": {"uri": "Candidate"},
    }

    # --- Top-level fields in schema order ---
    for field_def in schema.top_level_fields:
        fid = field_def.field_id
        raw_value = fields.personal.get(fid)

        if raw_value is None:
            if fid in DEFAULTS:
                candidate[fid] = DEFAULTS[fid]
            continue

        if field_def.field_type == "Picklist" and field_def.picklist_id:
            option_id = mapper.match_id(field_def.picklist_id, raw_value)
            if option_id:
                candidate[fid] = {"id": option_id}
            else:
                candidate[fid] = raw_value
        elif field_def.field_type == "DateTime":
            date_val = to_date_string(raw_value)
            if date_val:
                candidate[fid] = date_val
            else:
                candidate[fid] = raw_value
        elif field_def.field_type == "Boolean":
            candidate[fid] = str(raw_value).lower()
        else:
            candidate[fid] = raw_value

    # --- Section fields in schema order ---
    section_order = list(schema.sections.keys())
    for section_name in section_order:
        attr_name = SECTION_DATA_MAP.get(section_name)
        if not attr_name:
            continue
        entries = getattr(fields, attr_name, [])
        _assemble_section(candidate, section_name, entries, schema, mapper)

    return [candidate]


def _assemble_section(
    candidate: dict,
    section_name: str,
    entries: list[dict[str, str]],
    schema: Schema,
    mapper: PicklistMapper,
):
    if not entries:
        return

    field_defs = schema.sections.get(section_name, [])
    field_map: dict[str, FieldDef] = {}
    key_order: list[str] = []
    for fd in field_defs:
        if fd.nested_key:
            field_map[fd.nested_key] = fd
            key_order.append(fd.nested_key)

    results = []
    for entry in entries:
        record: dict = {}
        # Iterate in schema field order, not extraction order
        for key in key_order:
            raw_value = entry.get(key)
            if not raw_value:
                continue

            fd = field_map.get(key)
            if fd and fd.field_type == "Picklist" and fd.picklist_id:
                option_id = mapper.match_id(fd.picklist_id, raw_value)
                if option_id:
                    record[key] = option_id
                else:
                    record[key] = raw_value
            elif fd and fd.field_type == "DateTime":
                date_val = to_date_string(raw_value, default_ongoing=True)
                if date_val:
                    record[key] = date_val
                else:
                    record[key] = raw_value
            else:
                record[key] = raw_value

        if record:
            results.append(record)

    if results:
        candidate[section_name] = {"results": results}


def to_json_string(data: list[dict], indent: int = 4) -> str:
    return json.dumps(data, indent=indent, ensure_ascii=False)


if __name__ == "__main__":
    from schema_loader import load_schema
    from text_extractor import extract
    from field_extractor import extract_fields
    import sys

    if len(sys.argv) > 1:
        schema = load_schema()
        mapper = PicklistMapper(schema)

        doc = extract(sys.argv[1])
        fields = extract_fields(doc)
        result = assemble_json(fields, schema, mapper)
        print(to_json_string(result))
    else:
        print("Usage: python json_assembler.py <file.pdf|file.docx>")
