from dataclasses import dataclass

import pytest

from app.models.policy_documents import PolicyDocumentType
from app.models.scan_findings import CategoryType, FindingType, RiskType
from app.services.ai_provider import AIProvider, AIProviderError
from app.services.policy_generator import (
    build_policy_prompt,
    generate_policy_content,
    next_version,
)


@dataclass
class FindingFalso:
    finding_type: FindingType
    risk: RiskType = RiskType.medium
    categoria_dado_pessoal: CategoryType = CategoryType.email
    location: str = "https://site.com.br > formulário > campo 'email'"


class ProviderEspiao(AIProvider):
    def __init__(self) -> None:
        self.prompt_recebido = ""

    def generate(self, prompt: str) -> str:
        self.prompt_recebido = prompt
        return "conteúdo gerado"


class ProviderQuebrado(AIProvider):
    def generate(self, prompt: str) -> str:
        raise AIProviderError("fora do ar")


class TestBuildPolicyPrompt:
    def test_privacy_policy_inclui_apenas_achados_de_formulario(self):
        achados = [
            FindingFalso(FindingType.FORM, categoria_dado_pessoal=CategoryType.cpf),
            FindingFalso(FindingType.COOKIES),
        ]

        prompt = build_policy_prompt(
            PolicyDocumentType.PRIVACY_POLICY, "Padaria LTDA", "https://x.com", achados
        )

        assert "cpf" in prompt
        assert "cookie" not in prompt.lower().split("achados")[-1][:200]

    def test_cookie_notice_ignora_achado_de_formulario(self):
        achados = [
            FindingFalso(
                FindingType.FORM,
                categoria_dado_pessoal=CategoryType.cpf,
                location="https://x.com > formulário > campo 'cpf'",
            ),
            FindingFalso(
                FindingType.COOKIES,
                categoria_dado_pessoal=CategoryType.other,
                location="https://x.com > cookie '_ga'",
            ),
        ]

        prompt = build_policy_prompt(
            PolicyDocumentType.COOKIE_NOTICE, "X", "https://x.com", achados
        )

        secao_achados = prompt.split("## Cookies")[1].split("## O que escrever")[0]
        assert "cookie '_ga'" in secao_achados
        assert "campo 'cpf'" not in secao_achados

    def test_sem_achados_relevantes_diz_isso_explicitamente(self):
        prompt = build_policy_prompt(PolicyDocumentType.COOKIE_NOTICE, "X", "https://x.com", [])

        assert "Nenhum achado relevante registrado." in prompt

    def test_inclui_nome_da_empresa_e_url(self):
        prompt = build_policy_prompt(
            PolicyDocumentType.PRIVACY_POLICY, "Padaria LTDA", "https://padaria.com", []
        )

        assert "Padaria LTDA" in prompt
        assert "https://padaria.com" in prompt

    def test_todo_tipo_de_documento_tem_prompt(self):
        """Um tipo novo no enum sem prompt correspondente só seria descoberto
        quando um cliente clicasse em "gerar" — melhor quebrar aqui."""
        for tipo in PolicyDocumentType:
            assert build_policy_prompt(tipo, "X", "https://x.com", [])

    def test_terms_of_use_inclui_apenas_achados_de_formulario(self):
        achados = [
            FindingFalso(
                FindingType.FORM,
                location="https://x.com > formulário > campo 'email'",
            ),
            FindingFalso(
                FindingType.THIRD_PARTY_SCRIPT,
                categoria_dado_pessoal=CategoryType.other,
                location="https://x.com > script 'googletagmanager.com'",
            ),
        ]

        prompt = build_policy_prompt(
            PolicyDocumentType.TERMS_OF_USE, "Padaria LTDA", "https://x.com", achados
        )

        assert "Termos de Uso" in prompt
        assert "campo 'email'" in prompt
        assert "googletagmanager" not in prompt


class TestGeneratePolicyContent:
    def test_usa_o_texto_devolvido_pelo_provedor(self):
        espiao = ProviderEspiao()

        conteudo = generate_policy_content(
            espiao, PolicyDocumentType.PRIVACY_POLICY, "X", "https://x.com", []
        )

        assert conteudo == "conteúdo gerado"

    def test_falha_da_ia_propaga_erro(self):
        """Diferente do relatório executivo: um rascunho de política pela metade
        não tem valor de fallback determinístico, então a falha deve subir."""
        with pytest.raises(AIProviderError):
            generate_policy_content(
                ProviderQuebrado(), PolicyDocumentType.PRIVACY_POLICY, "X", "https://x.com", []
            )


class TestNextVersion:
    def test_primeira_versao_e_v1(self):
        assert next_version([]) == "v1"

    def test_incrementa_a_partir_da_maior_versao_existente(self):
        assert next_version(["v1", "v2", "v3"]) == "v4"

    def test_ignora_rotulo_de_versao_nao_numerico(self):
        assert next_version(["rascunho-inicial", "v2"]) == "v3"

    def test_ordem_de_insercao_nao_importa(self):
        assert next_version(["v5", "v1", "v3"]) == "v6"
