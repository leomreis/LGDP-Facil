"""Geração assistida de política de privacidade, termos de uso e aviso de cookies.

Mesma regra do relatório executivo: o conteúdo vem estritamente dos achados já
classificados deterministicamente — a IA não decide o que a empresa coleta, só
redige o texto a partir do que o scanner encontrou.
"""

from pathlib import Path

from app.models.policy_documents import PolicyDocumentType
from app.models.scan_findings import FindingType
from app.services.ai_provider import AIProvider, AIProviderError

PROMPTS_DIR = Path(__file__).parent / "prompts"

PROMPT_BY_TYPE: dict[PolicyDocumentType, str] = {
    PolicyDocumentType.PRIVACY_POLICY: "politica_privacidade.md",
    PolicyDocumentType.COOKIE_NOTICE: "aviso_cookies.md",
    PolicyDocumentType.TERMS_OF_USE: "termos_uso.md",
}


def _load_prompt(nome: str) -> str:
    return (PROMPTS_DIR / nome).read_text(encoding="utf-8")


def _format_findings_for_policy(findings, tipo: PolicyDocumentType) -> str:
    """Filtra os achados relevantes para o tipo de documento.

    O aviso de cookies só precisa saber de cookies/scripts; a política de
    privacidade e os termos de uso só precisam saber de dado pessoal coletado
    via formulário — incluir achado irrelevante confundiria a IA sobre o que o
    documento cobre.
    """
    if tipo is PolicyDocumentType.COOKIE_NOTICE:
        tipos_relevantes = (FindingType.COOKIES, FindingType.THIRD_PARTY_SCRIPT)
        relevantes = [f for f in findings if f.finding_type in tipos_relevantes]
    else:
        relevantes = [f for f in findings if f.finding_type == FindingType.FORM]

    if not relevantes:
        return "Nenhum achado relevante registrado."

    return "\n".join(
        f"- [{f.finding_type.value}] {f.categoria_dado_pessoal.value}: {f.location}"
        for f in relevantes
    )


def build_policy_prompt(
    tipo: PolicyDocumentType,
    nome_empresa: str,
    url: str,
    findings,
) -> str:
    if tipo not in PROMPT_BY_TYPE:
        raise ValueError(f"Geração de {tipo.value} ainda não suportada")

    return _load_prompt(PROMPT_BY_TYPE[tipo]).format(
        nome_empresa=nome_empresa,
        url=url,
        achados=_format_findings_for_policy(findings, tipo),
    )


def generate_policy_content(
    provider: AIProvider,
    tipo: PolicyDocumentType,
    nome_empresa: str,
    url: str,
    findings,
) -> str:
    """Gera o texto do documento. Propaga falha — diferente do relatório, um
    rascunho de política pela metade não tem valor de fallback determinístico."""
    prompt = build_policy_prompt(tipo, nome_empresa, url, findings)
    try:
        return provider.generate(prompt)
    except AIProviderError:
        raise


def next_version(previous_versions: list[str]) -> str:
    """Versões seguem o padrão 'v1', 'v2', ... A empresa pode ter documentos
    versionados manualmente antes; qualquer rótulo não numérico é ignorado no
    cálculo do próximo número, mas não impede a geração."""
    numeros = []
    for v in previous_versions:
        if v.lower().startswith("v") and v[1:].isdigit():
            numeros.append(int(v[1:]))
    return f"v{max(numeros, default=0) + 1}"
