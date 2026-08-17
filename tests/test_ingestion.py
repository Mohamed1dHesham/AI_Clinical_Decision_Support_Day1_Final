from collections import Counter

from src.ingestion import infer_sections, load_documents


def test_ingestion_metadata_and_unique_ids():
    chunks = load_documents()
    assert chunks

    ids = [item["id"] for item in chunks]
    assert len(ids) == len(set(ids))

    for item in chunks:
        md = item["metadata"]
        assert md["document_name"]
        assert md["document_id"] in {"HTN-NG136", "HTN-PDA-2019"}
        assert md["section"]
        assert md["section"] != "General"
        assert isinstance(md["page_number"], int)
        assert md["page_number"] >= 1
        assert md["chunk_id"] == item["id"]
        assert md["token_count"] > 0


def test_ng136_does_not_create_false_numeric_sections():
    chunks = load_documents()
    ng = [x for x in chunks if x["metadata"]["document_id"] == "HTN-NG136"]
    sections = {x["metadata"]["section"] for x in ng}

    assert "4.5 mmol/l." not in sections
    assert "1.5 Identifying who to refer for same-day specialist review ............................................................. 24" not in sections
    assert "1.3 Assessing cardiovascular risk and target organ" not in sections
    assert "1.3 Assessing cardiovascular risk and target organ damage" in sections


def test_patient_decision_aid_sections_are_known_headings():
    chunks = load_documents()
    pda = [x for x in chunks if x["metadata"]["document_id"] == "HTN-PDA-2019"]
    assert pda
    sections = {x["metadata"]["section"] for x in pda}

    forbidden_fragments = ("may help make", "taking an ACE")
    assert not any(any(fragment in section for fragment in forbidden_fragments) for section in sections)


def test_wrapped_ng136_heading_is_reconstructed():
    text = """1.3 Assessing cardiovascular risk and target organ\ndamage\n1.3.1 Use a formal estimation of cardiovascular risk."""
    blocks = infer_sections(text, "HTN-NG136")
    assert blocks[0][0] == "1.3 Assessing cardiovascular risk and target organ damage"
    assert "formal estimation" in blocks[0][1]


def test_front_matter_is_used_instead_of_ambiguous_general_section():
    chunks = load_documents()
    assert all(x["metadata"]["section"] != "General" for x in chunks)


def test_section_counts_are_reasonable():
    chunks = load_documents()
    counts = Counter(x["metadata"]["document_id"] for x in chunks)
    assert counts["HTN-NG136"] > 0
    assert counts["HTN-PDA-2019"] > 0
