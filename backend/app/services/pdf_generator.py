"""Geração de PDF do relatório de conformidade, sob demanda.

Gerado a cada requisição, não persistido em disco/storage — o relatório é
pequeno e a geração é rápida (fpdf2 é puro Python, sem dependência de sistema
como o WeasyPrint precisaria). Se o volume justificar cachear depois, o
`pdf_url` de `Report` já existe no schema para isso.
"""

from datetime import datetime, timezone

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.models.scan_findings import ScanFinding

AVISO_LEGAL = (
    "Este relatorio e gerado automaticamente e nao substitui avaliacao juridica profissional."
)


def _line(pdf: FPDF, height: float, texto: str) -> None:
    """multi_cell deixa o cursor no fim da última linha por padrão (new_x=RIGHT),
    o que esgota a largura disponível na chamada seguinte. Sempre volta para a
    margem esquerda depois de escrever."""
    pdf.multi_cell(0, height, _sanitize(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _sanitize(texto: str) -> str:
    """As fontes core do fpdf2 (Helvetica) só cobrem Latin-1. Acentos comuns do
    português (á, ç, ã...) estão em Latin-1 e passam direto; o que não couber
    (ex.: travessão "—", aspas tipográficas que a IA às vezes gera) vira "?"
    em vez de quebrar a geração do PDF inteiro."""
    return texto.encode("latin-1", errors="replace").decode("latin-1")


def generate_report_pdf(
    company_name: str,
    scan_url: str,
    score: float,
    resumo_executivo: str,
    findings: list[ScanFinding],
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    _line(pdf, 10, "Relatorio de Conformidade LGPD")

    pdf.set_font("Helvetica", "", 11)
    _line(pdf, 7, f"Empresa: {company_name}")
    _line(pdf, 7, f"Site analisado: {scan_url}")
    gerado_em = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    _line(pdf, 7, f"Gerado em: {gerado_em}")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    _line(pdf, 9, f"Score de conformidade: {score:.1f} / 100")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    _line(pdf, 8, "Resumo executivo")
    pdf.set_font("Helvetica", "", 10)
    _line(pdf, 6, resumo_executivo)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    _line(pdf, 8, f"Achados ({len(findings)})")
    pdf.set_font("Helvetica", "", 9)
    if not findings:
        _line(pdf, 6, "Nenhum achado registrado.")
    for finding in findings:
        linha = (
            f"[{finding.risk.value.upper()}] {finding.finding_type.value} / "
            f"{finding.categoria_dado_pessoal.value} - {finding.location}"
        )
        _line(pdf, 6, linha)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    _line(pdf, 5, AVISO_LEGAL)

    return bytes(pdf.output())
