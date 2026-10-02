from dataclasses import dataclass

from app.models.scan_findings import CategoryType, FindingType, RiskType
from app.services.pdf_generator import generate_report_pdf


@dataclass
class FindingFalso:
    risk: RiskType = RiskType.high
    categoria_dado_pessoal: CategoryType = CategoryType.cpf
    finding_type: FindingType = FindingType.FORM
    location: str = "https://site.com.br > formulário > campo 'cpf'"


def _e_um_pdf_valido(conteudo: bytes) -> bool:
    return conteudo.startswith(b"%PDF-")


class TestGenerateReportPdf:
    def test_gera_bytes_de_pdf_valido(self):
        pdf = generate_report_pdf("Padaria LTDA", "https://padaria.com.br", 71.0, "Resumo.", [])

        assert _e_um_pdf_valido(pdf)

    def test_funciona_sem_nenhum_achado(self):
        pdf = generate_report_pdf("X", "https://x.com", 100.0, "Sem achados.", [])

        assert _e_um_pdf_valido(pdf)
        assert len(pdf) > 0

    def test_funciona_com_varios_achados(self):
        achados = [FindingFalso() for _ in range(15)]

        pdf = generate_report_pdf("X", "https://x.com", 10.0, "Muitos achados.", achados)

        assert _e_um_pdf_valido(pdf)

    def test_nao_quebra_com_caractere_fora_do_latin1_no_resumo(self):
        """A IA às vezes devolve travessão "—" ou aspas tipográficas — que não
        existem em Latin-1, a única codificação que a fonte core do fpdf2 cobre."""
        resumo_com_travessao = "Achado crítico — revise o formulário — antes de publicar."

        pdf = generate_report_pdf("X", "https://x.com", 50.0, resumo_com_travessao, [])

        assert _e_um_pdf_valido(pdf)

    def test_acentos_comuns_do_portugues_nao_quebram_a_geracao(self):
        pdf = generate_report_pdf(
            "Padaria São João Ltda",
            "https://padaria.com.br",
            85.5,
            "Análise concluída sem exposição crítica de informação pessoal.",
            [],
        )

        assert _e_um_pdf_valido(pdf)
