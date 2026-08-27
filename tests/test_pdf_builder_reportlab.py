"""Tests for FoundationDesignJm PDF report generation with reportlab."""
import tempfile
from pathlib import Path
import pytest
from foundationdesignjm.reports.pdf_builder import Report


def test_pdf_builder_generates_valid_pdf_file():
    rep = Report(title="Memoria de Calculo de Cimentacion", subtitle="Zapata Aislada EC7", project="PRJ-001", author="Jesus Murgas")
    rep.add_section("1. Bases de Calculo")
    rep.add_paragraph("Diseno de cimentacion superficial segun Eurocodigo 7 (EN 1997-1).")
    rep.add_subsection("1.1 Parametros Geometricos y de Suelo")
    rep.add_kv_table([
        ("Ancho B (m)", 2.50),
        ("Largo L (m)", 3.00),
        ("Canto H (m)", 0.80),
        ("Tension admisible (kPa)", 250.0),
    ])
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_file = Path(tmpdir) / "test_report.pdf"
        out_path = rep.save(str(pdf_file))
        assert Path(out_path).exists()
        pdf_bytes = Path(out_path).read_bytes()
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 500
