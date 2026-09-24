"""Invariants of the synthetic training data (also a broad extractor regression test)."""
import json
import random

import pytest

from canonical import SYSTEM_PROMPT, build_messages, find_hints, ground, order_canonical
from text_extractor import extract
from training.render import TEMPLATES, render
from training.synth import ProfileGenerator


@pytest.mark.parametrize("template", sorted(TEMPLATES))
def test_every_gold_value_survives_extraction(tmp_path, template):
    gen = ProfileGenerator(seed=11)
    lost, total = 0, 0
    for i in range(6):
        gen.reseed(1000 + i)
        profile = gen.generate(form_like="form" in template)
        path, _ = render(profile, str(tmp_path), f"cv{i}", random.Random(i), template=template)
        doc = extract(path)
        gold = order_canonical(profile.gold())
        _, conf = ground(gold, doc.layout_text, find_hints(doc.layout_text, doc.links), min_score=0.9)
        total += len(conf)
        lost += sum(1 for c in conf.values() if c < 0.9)
    assert total > 30
    assert lost / total < 0.03, f"{template}: {lost}/{total} gold values not found in extracted text"


def test_dataset_records(tmp_path):
    from training import build_dataset as bd
    cfg = {"seed": 5, "docs_dir": None, "max_chars": 12000, "chunk_prob": 1.0, "chunk_chars": 600,
           "templates": None, "format": "prompt_completion"}
    bd._init_worker(cfg)
    res = bd.make_synthetic(3)
    assert "records" in res, res
    for rec in res["records"]:
        system, user = rec["prompt"]
        assert system == {"role": "system", "content": SYSTEM_PROMPT}
        assert user["content"].startswith("CV TEXT:\n<<<\n")
        target = json.loads(rec["completion"][0]["content"])
        assert set(target) <= {"personal", "education", "experience", "languages", "certificates",
                               "awards", "courses", "family"}
        text = user["content"].split("<<<\n", 1)[1].rsplit("\n>>>", 1)[0]
        assert build_messages(text, find_hints(text))[1]["content"].split("DETECTED")[0] == \
            user["content"].split("DETECTED")[0]
