from dataclasses import dataclass

import pytest

from app.models.scan_findings import CategoryType, FindingType, RiskType
from app.services.ai_provider import AIProvider, AIProviderError, FakeProvider
from app.services.report_generator import (
    SCORE_MAXIMO,
    build_prompt,
    calculate_score,
    generate_executive_summary,
    summarize_by_risk,
)


@dataclass
class FindingFalso:
    """Espelha os campos de ScanFinding usados pelo gerador, sem precisar de banco."""

    risk: RiskType
    categoria_dado_pessoal: CategoryType = CategoryType.cpf
    finding_type: FindingType = FindingType.FORM
    location: str = "https://site.com.br > formulário > campo 'cpf'"


class ProviderQuebrado(AIProvider):
    def generate(self, prompt: str) -> str:
        raise AIProviderError("cota esgotada")


class ProviderEspiao(AIProvider):
    def __init__(self) -> None:
        self.prompt_recebido = ""

    def generate(self, prompt: str) -> str:
        self.prompt_recebido = prompt
        return "resumo gerado"


class TestCalculateScore:
    def test_site_sem_achado_tem_score_maximo(self):
        assert calculate_score([]) == SCORE_MAXIMO

    def test_risco_alto_desconta_mais_que_medio_que_baixo(self):
        alto = calculate_score([FindingFalso(RiskType.high)])
        medio = calculate_score([FindingFalso(RiskType.medium)])
        baixo = calculate_score([FindingFalso(RiskType.low)])

        assert alto < medio < baixo < SCORE_MAXIMO

    def test_score_nunca_fica_negativo(self):
        achados = [FindingFalso(RiskType.high)] * 50

        assert calculate_score(achados) == 0.0

    def test_score_e_deterministico(self):
        achados = [FindingFalso(RiskType.high), FindingFalso(RiskType.low)]

        assert calculate_score(achados) == calculate_score(achados)

    def test_score_de_referencia(self):
        """Um alto (15) + dois médios (12) + um baixo (2) = 100 - 29."""
        achados = [
            FindingFalso(RiskType.high),
            FindingFalso(RiskType.medium),
            FindingFalso(RiskType.medium),
            FindingFalso(RiskType.low),
        ]

        assert calculate_score(achados) == 71.0


class TestSummarizeByRisk:
    def test_conta_achados_por_risco(self):
        achados = [
            FindingFalso(RiskType.high),
            FindingFalso(RiskType.high),
            FindingFalso(RiskType.medium),
        ]

        assert summarize_by_risk(achados) == {"high": 2, "medium": 1, "low": 0}


class TestBuildPrompt:
    def test_prompt_inclui_empresa_url_e_achados(self):
        prompt = build_prompt("Padaria LTDA", "https://site.com.br", [FindingFalso(RiskType.high)])

        assert "Padaria LTDA" in prompt
        assert "https://site.com.br" in prompt
        assert "cpf" in prompt

    def test_prompt_agrupa_por_risco(self):
        prompt = build_prompt("X", "https://x.com", [FindingFalso(RiskType.high)])

        assert "Risco high" in prompt

    def test_prompt_diz_explicitamente_quando_nao_ha_achado(self):
        prompt = build_prompt("X", "https://x.com", [])

        assert "Nenhum achado registrado." in prompt

    def test_prompt_proibe_a_ia_de_reclassificar(self):
        """A classificação é determinística; o prompt precisa blindar isso."""
        prompt = build_prompt("X", "https://x.com", [])

        assert "não reclassifique" in prompt.lower()


class TestGenerateExecutiveSummary:
    def test_usa_o_texto_devolvido_pelo_provedor(self):
        espiao = ProviderEspiao()

        resumo = generate_executive_summary(espiao, "X", "https://x.com", [])

        assert resumo == "resumo gerado"
        assert "X" in espiao.prompt_recebido

    def test_falha_da_ia_nao_perde_o_scan(self):
        achados = [FindingFalso(RiskType.high), FindingFalso(RiskType.low)]

        resumo = generate_executive_summary(ProviderQuebrado(), "X", "https://x.com", achados)

        assert "2 achado(s)" in resumo
        assert "1 de risco alto" in resumo

    def test_provider_fake_nao_precisa_de_rede(self):
        resumo = generate_executive_summary(FakeProvider(), "X", "https://x.com", [])

        assert "fake" in resumo


class TestGetAIProvider:
    @pytest.mark.parametrize(
        ("escolha", "classe"),
        [
            ("gemini", "GeminiProvider"),
            ("anthropic", "AnthropicProvider"),
            ("fake", "FakeProvider"),
        ],
    )
    def test_seleciona_o_adaptador_pela_variavel_de_ambiente(self, escolha, classe):
        from app.core.config import Settings
        from app.services.ai_provider import get_ai_provider

        settings = Settings()
        settings.ai_provider = escolha

        assert type(get_ai_provider(settings)).__name__ == classe

    def test_provider_desconhecido_falha_alto(self):
        from app.core.config import Settings
        from app.services.ai_provider import get_ai_provider

        settings = Settings()
        settings.ai_provider = "chatgpt"

        with pytest.raises(AIProviderError, match="chatgpt"):
            get_ai_provider(settings)
