from app.services.dsm_ingestion import DsmIngestionService


def service():
    return DsmIngestionService(session=None)  # type: ignore[arg-type]


def valid_doc(**overrides):
    doc = {
        "item_id": "tdah",
        "name": "TDAH",
        "chapter_id": "01",
        "chapter_name": "Neurodesenvolvimento",
        "category": "FULL",
        "estrutura_diagnostica": "polythetic_clusters_simetricos",
        "ui_mode": "structured_full",
        "render_structured_interview": True,
        "diagnostic_rule": "A1 ou A2 com prejuízo clínico.",
        "severity": {"type": "contagem_sintomas_e_prejuizo", "has_formal_severity": True},
    }
    doc.update(overrides)
    return doc


def test_importador_rejeita_documento_sem_item_id_name():
    errors, _ = service().validate_all([{k: v for k, v in valid_doc().items() if k not in {"item_id", "name"}}], [])
    assert errors
    assert "missing" in errors[0]


def test_importador_rejeita_full_short_sem_diagnostic_rule():
    doc = valid_doc()
    doc.pop("diagnostic_rule")
    errors, _ = service().validate_all([doc], [])
    assert any("diagnostic_rule" in error for error in errors)


def test_importador_nao_permite_minimal_exclude_em_documents():
    errors, _ = service().validate_all([valid_doc(category="MINIMAL")], [])
    assert any("invalid category" in error for error in errors)
