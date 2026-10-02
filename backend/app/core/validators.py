"""Validadores de documentos brasileiros compartilhados entre schemas.

Fica em core/ (não em services/personal_data_classifier.py) porque validar o
CNPJ de cadastro da empresa é uma regra de entrada de dados, diferente de
classificar dado pessoal encontrado num scan — são conceitos vizinhos, não o
mesmo código.
"""

import re


def _calc_digito_verificador(numeros: list[int], pesos: list[int]) -> int:
    soma = sum(n * p for n, p in zip(numeros, pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def is_valid_cnpj(candidato: str) -> bool:
    """Valida os dois dígitos verificadores do CNPJ (Receita Federal).

    Mesma motivação do validador de CPF: sem isso, qualquer string de 14
    dígitos vira um cadastro de empresa "válido", incluindo erros de digitação
    óbvios (o mais comum: um dígito trocado ao copiar e colar).
    """
    digitos = [int(c) for c in re.sub(r"\D", "", candidato)]
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False

    pesos_d1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_d2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    if digitos[12] != _calc_digito_verificador(digitos[:12], pesos_d1):
        return False
    return digitos[13] == _calc_digito_verificador(digitos[:13], pesos_d2)
