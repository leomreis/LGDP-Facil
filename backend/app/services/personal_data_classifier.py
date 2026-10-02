"""Classificação determinística de dado pessoal.

Regra de produto: a IA nunca decide o que é dado pessoal. Essa decisão é tomada
aqui, por regex e validação de formato, para ser auditável e reproduzível — a IA
só recebe os achados já classificados e escreve o relatório em linguagem natural.
"""

import re
import unicodedata
from dataclasses import dataclass

from app.models.scan_findings import CategoryType, RiskType

# Risco por categoria, na ótica da LGPD: o que identifica unicamente a pessoa
# (CPF) ou revela sua localização física (endereço) pesa mais que um contato.
CATEGORY_RISK: dict[CategoryType, RiskType] = {
    CategoryType.cpf: RiskType.high,
    CategoryType.address: RiskType.high,
    CategoryType.email: RiskType.medium,
    CategoryType.phone: RiskType.medium,
    CategoryType.full_name: RiskType.medium,
    CategoryType.other: RiskType.low,
}

# Palavras que aparecem em name/id/placeholder/label de campos de formulário.
# Ordem importa: a primeira categoria que casar vence, e "cpf" é mais específico
# que "nome" (um campo "nome_cpf" deve cair em cpf).
FIELD_KEYWORDS: list[tuple[CategoryType, tuple[str, ...]]] = [
    (CategoryType.cpf, ("cpf", "documento", "doc", "rg", "cnh")),
    (
        CategoryType.address,
        (
            "endereco",
            "logradouro",
            "rua",
            "avenida",
            "bairro",
            "cidade",
            "estado",
            "cep",
            "zip",
            "address",
            "numero",
            "complemento",
        ),
    ),
    (CategoryType.email, ("email", "e-mail", "mail")),
    (CategoryType.phone, ("telefone", "celular", "whatsapp", "fone", "phone", "tel", "mobile")),
    (CategoryType.full_name, ("nome", "sobrenome", "name", "fullname")),
]

# type="email" / type="tel" do HTML são declarações explícitas do próprio site.
INPUT_TYPE_CATEGORY: dict[str, CategoryType] = {
    "email": CategoryType.email,
    "tel": CategoryType.phone,
}

CPF_PATTERN = re.compile(r"\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b")
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
CEP_PATTERN = re.compile(r"\b\d{5}-\d{3}\b")
PHONE_PATTERN = re.compile(
    r"(?:\+55[\s-]?)?"  # DDI opcional
    r"(?:\(\d{2}\)|\b\d{2})[\s-]?"  # DDD com ou sem parênteses
    r"9?\d{4}[\s-]?\d{4}\b"  # número, com o 9 opcional de celular
)


@dataclass(frozen=True)
class FormField:
    """Um campo de formulário encontrado pelo scanner."""

    name: str = ""
    input_type: str = ""
    label: str = ""
    placeholder: str = ""


@dataclass(frozen=True)
class Classification:
    category: CategoryType
    risk: RiskType


def _normalize(texto: str) -> str:
    """Minúsculas e sem acento, para 'Endereço' casar com a keyword 'endereco'."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


def is_valid_cpf(candidato: str) -> bool:
    """Valida os dois dígitos verificadores do CPF.

    Sem isso, qualquer sequência de 11 dígitos (um código de pedido, um número de
    protocolo) viraria um achado de risco alto e encheria o relatório de ruído.
    """
    digitos = [int(c) for c in re.sub(r"\D", "", candidato)]
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False

    for tamanho in (9, 10):
        soma = sum(d * (tamanho + 1 - i) for i, d in enumerate(digitos[:tamanho]))
        resto = (soma * 10) % 11
        esperado = 0 if resto == 10 else resto
        if digitos[tamanho] != esperado:
            return False
    return True


def classify_field(field: FormField) -> Classification:
    """Classifica um campo de formulário pelo que o site declara sobre ele.

    Campos costumam vir vazios (o scanner lê a página, não os dados submetidos),
    então a evidência aqui é o rótulo, não o valor.
    """
    categoria = INPUT_TYPE_CATEGORY.get(_normalize(field.input_type))
    if categoria is None:
        pistas = _normalize(" ".join((field.name, field.label, field.placeholder)))
        categoria = next(
            (
                cat
                for cat, palavras in FIELD_KEYWORDS
                if any(palavra in pistas for palavra in palavras)
            ),
            CategoryType.other,
        )

    return Classification(category=categoria, risk=CATEGORY_RISK[categoria])


def detect_in_text(texto: str) -> list[Classification]:
    """Detecta dado pessoal exposto em texto livre da página.

    Cada categoria entra no máximo uma vez: o relatório precisa saber *que tipo* de
    dado está exposto e onde, não repetir o mesmo achado por ocorrência.
    """
    encontradas: list[CategoryType] = []

    if any(is_valid_cpf(m.group(0)) for m in CPF_PATTERN.finditer(texto)):
        encontradas.append(CategoryType.cpf)

    if EMAIL_PATTERN.search(texto):
        encontradas.append(CategoryType.email)

    # CPF e telefone competem pelas mesmas sequências de dígitos; os CPFs válidos
    # já reconhecidos saem do texto antes da varredura de telefone.
    texto_sem_cpf = CPF_PATTERN.sub(lambda m: "" if is_valid_cpf(m.group(0)) else m.group(0), texto)
    if PHONE_PATTERN.search(texto_sem_cpf):
        encontradas.append(CategoryType.phone)

    if CEP_PATTERN.search(texto):
        encontradas.append(CategoryType.address)

    return [Classification(category=cat, risk=CATEGORY_RISK[cat]) for cat in encontradas]
