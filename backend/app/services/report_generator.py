"""Geração do relatório de conformidade a partir dos achados do scan.

Divisão de responsabilidade: o **score é calculado aqui**, por fórmula fixa, e a
IA só escreve o texto. Um score que variasse a cada chamada da IA seria inútil
para a PME acompanhar evolução entre scans.
"""

from collections import Counter
from pathlib import Path

from app.models.scan_findings import RiskType
from app.services.ai_provider import AIProvider, AIProviderError

PROMPTS_DIR = Path(__file__).parent / "prompts"

SCORE_MAXIMO = 100.0

# Peso de cada achado no desconto do score. Calibrado para que uma empresa com um
# punhado de problemas médios ainda fique na faixa "atenção", e não em "crítico".
PESO_POR_RISCO: dict[RiskType, float] = {
    RiskType.high: 15.0,
    RiskType.medium: 6.0,
    RiskType.low: 2.0,
}


def calculate_score(findings) -> float:
    """Score de 0 a 100. Começa em 100 e desconta por achado, conforme o risco."""
    desconto = sum(PESO_POR_RISCO[f.risk] for f in findings)
    return round(max(0.0, SCORE_MAXIMO - desconto), 1)


def _load_prompt(nome: str) -> str:
    return (PROMPTS_DIR / nome).read_text(encoding="utf-8")


def _format_findings(findings) -> str:
    if not findings:
        return "Nenhum achado registrado."

    por_risco = {RiskType.high: [], RiskType.medium: [], RiskType.low: []}
    for f in findings:
        por_risco[f.risk].append(f)

    linhas: list[str] = []
    for risco in (RiskType.high, RiskType.medium, RiskType.low):
        if not por_risco[risco]:
            continue
        linhas.append(f"\n### Risco {risco.value}")
        for f in por_risco[risco]:
            linhas.append(
                f"- [{f.finding_type.value}] dado do tipo "
                f"'{f.categoria_dado_pessoal.value}' em: {f.location}"
            )
    return "\n".join(linhas)


def build_prompt(nome_empresa: str, url: str, findings) -> str:
    return _load_prompt("relatorio_executivo.md").format(
        nome_empresa=nome_empresa,
        url=url,
        total_achados=len(findings),
        achados=_format_findings(findings),
    )


def summarize_by_risk(findings) -> dict[str, int]:
    contagem = Counter(f.risk.value for f in findings)
    return {risco.value: contagem.get(risco.value, 0) for risco in RiskType}


def generate_executive_summary(
    provider: AIProvider,
    nome_empresa: str,
    url: str,
    findings,
) -> str:
    """Gera o texto do relatório. Falha de IA não pode perder o scan já feito.

    Se o provedor cair, devolvemos um resumo determinístico mínimo em vez de
    propagar o erro: os achados e o score continuam válidos e úteis sem o texto.
    """
    try:
        return provider.generate(build_prompt(nome_empresa, url, findings))
    except AIProviderError:
        contagem = summarize_by_risk(findings)
        return (
            "Não foi possível gerar o resumo em linguagem natural desta vez. "
            f"A varredura encontrou {len(findings)} achado(s): "
            f"{contagem['high']} de risco alto, {contagem['medium']} de risco médio "
            f"e {contagem['low']} de risco baixo. Consulte a lista detalhada de "
            "achados e tente gerar o resumo novamente."
        )
