import pytest

from app.core.validators import is_valid_cnpj


class TestIsValidCnpj:
    @pytest.mark.parametrize(
        "cnpj",
        [
            "11.222.333/0001-81",
            "11222333000181",
            "11222333/0001-81",
        ],
    )
    def test_aceita_cnpj_valido_em_formatos_variados(self, cnpj):
        assert is_valid_cnpj(cnpj) is True

    @pytest.mark.parametrize(
        "cnpj",
        [
            "11.222.333/0001-80",  # último dígito errado
            "11.222.333/0001-91",  # primeiro dígito errado
            "11.111.111/1111-11",  # todos iguais: passa na fórmula, mas não é CNPJ real
            "12345678000199",  # 14 dígitos, mas dígito verificador não bate
            "123456780001",  # 12 dígitos
            "1234567800019912",  # 16 dígitos
            "",
        ],
    )
    def test_rejeita_cnpj_invalido(self, cnpj):
        assert is_valid_cnpj(cnpj) is False
