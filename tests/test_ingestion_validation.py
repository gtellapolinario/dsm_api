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
    errors, _ = service().validate_all(
        [{k: v for k, v in valid_doc().items() if k not in {"item_id", "name"}}], []
    )
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


def test_load_final_json_herda_metadados_do_capitulo(tmp_path):
    release_file = tmp_path / "01_capitulo.json"
    release_file.write_text(
        """
        {
          "chapter_id": "01",
          "chapter_name": "Neurodesenvolvimento",
          "items": [
            {
              "id": "tdah",
              "name": "TDAH",
              "category": "FULL",
              "estrutura_diagnostica": "polythetic_clusters_simetricos",
              "ui_mode": "structured_full",
              "render_structured_interview": true,
              "diagnostic_rule": "A1 ou A2 com prejuízo clínico."
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    docs = service().load_final_json(tmp_path)

    assert docs[0]["chapter_id"] == "01"
    assert docs[0]["chapter_name"] == "Neurodesenvolvimento"
    errors, _ = service().validate_all(docs, [])
    assert errors == []


def test_load_registry_file_aceita_entries(tmp_path):
    registry_file = tmp_path / "minimal_all.json"
    registry_file.write_text(
        """
        {
          "registry_type": "minimal",
          "entries": [
            {
              "id": "atraso_global",
              "name": "Atraso Global do Desenvolvimento",
              "chapter_id": "01",
              "chapter_name": "Neurodesenvolvimento",
              "render_structured_interview": false
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    rows = service().load_registry_file(registry_file, "MINIMAL")

    assert len(rows) == 1
    assert rows[0]["category"] == "MINIMAL"
    errors, _ = service().validate_all([], rows)
    assert errors == []
