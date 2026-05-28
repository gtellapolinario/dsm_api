from app.services.chunking import DsmChunkingService
from tests.test_ingestion_validation import valid_doc


def test_gera_chunks_nao_vazios_para_documento_exemplo():
    chunks = DsmChunkingService().build_chunks(valid_doc(severity={"type": "contagem_sintomas_e_prejuizo", "levels": ["leve", "moderado"]}))
    assert chunks
    assert all(chunk.chunk_text for chunk in chunks)


def test_gera_chunk_diagnostic_rule():
    chunks = DsmChunkingService().build_chunks(valid_doc())
    assert any(chunk.chunk_type == "diagnostic_rule" for chunk in chunks)


def test_gera_chunk_severity_quando_houver():
    chunks = DsmChunkingService().build_chunks(valid_doc(severity={"type": "ordinal_simples", "levels": ["leve"]}))
    assert any(chunk.chunk_type == "severity" for chunk in chunks)
