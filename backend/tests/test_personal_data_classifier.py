import pytest

from app.models.scan_findings import CategoryType, RiskType
from app.services.personal_data_classifier import (
    FormField,
    classify_field,
    detect_in_text,
    is_valid_cpf,
)

# CPFs sintéticos com dígitos verificadores corretos, gerados para teste.
CPF_VALIDO = "529.982.247-25"
CPF_VALIDO_SEM_MASCARA = "52998224725"


class TestIsValidCpf:
    @pytest.mark.parametrize(
        "cpf",
        [
            CPF_VALIDO,
            CPF_VALIDO_SEM_MASCARA,
            "529982247-25",
            "529.982.24725",
        ],
    )
    def test_aceita_cpf_valido_em_formatos_variados(self, cpf):
        assert is_valid_cpf(cpf) is True

    @pytest.mark.parametrize(
        "cpf",
        [
            "529.982.247-26",  # último dígito verificador errado
            "529.982.247-15",  # primeiro dígito verificador errado
            "111.111.111-11",  # todos iguais: passa na fórmula, mas não é CPF real
            "000.000.000-00",
            "1234567890",  # 10 dígitos
            "123456789012",  # 12 dígitos
            "",
        ],
    )
    def test_rejeita_cpf_invalido(self, cpf):
        assert is_valid_cpf(cpf) is False


class TestClassifyField:
    @pytest.mark.parametrize(
        ("field", "esperado"),
        [
            (FormField(name="cpf"), CategoryType.cpf),
            (FormField(name="numero_documento"), CategoryType.cpf),
            (FormField(label="CPF do titular"), CategoryType.cpf),
            (FormField(name="email"), CategoryType.email),
            (FormField(name="contato", input_type="email"), CategoryType.email),
            (FormField(placeholder="seu@email.com.br"), CategoryType.email),
            (FormField(name="telefone"), CategoryType.phone),
            (FormField(name="campo1", input_type="tel"), CategoryType.phone),
            (FormField(label="WhatsApp"), CategoryType.phone),
            (FormField(name="endereco"), CategoryType.address),
            (FormField(label="Endereço completo"), CategoryType.address),
            (FormField(name="cep"), CategoryType.address),
            (FormField(name="nome"), CategoryType.full_name),
            (FormField(label="Nome completo"), CategoryType.full_name),
            (FormField(name="assunto"), CategoryType.other),
            (FormField(), CategoryType.other),
        ],
    )
    def test_classifica_campo_pela_declaracao_do_site(self, field, esperado):
        assert classify_field(field).category is esperado

    def test_acento_no_rotulo_nao_impede_deteccao(self):
        assert classify_field(FormField(label="ENDEREÇO")).category is CategoryType.address

    def test_input_type_explicito_vence_a_keyword_do_name(self):
        """type="email" é declaração do próprio site e é evidência mais forte que o name."""
        field = FormField(name="nome", input_type="email")

        assert classify_field(field).category is CategoryType.email

    def test_cpf_e_mais_especifico_que_nome(self):
        assert classify_field(FormField(name="nome_cpf")).category is CategoryType.cpf

    @pytest.mark.parametrize(
        ("field", "risco"),
        [
            (FormField(name="cpf"), RiskType.high),
            (FormField(name="endereco"), RiskType.high),
            (FormField(name="email"), RiskType.medium),
            (FormField(name="telefone"), RiskType.medium),
            (FormField(name="nome"), RiskType.medium),
            (FormField(name="assunto"), RiskType.low),
        ],
    )
    def test_atribui_risco_conforme_a_categoria(self, field, risco):
        assert classify_field(field).risk is risco


class TestDetectInText:
    def test_detecta_cpf_valido_exposto_na_pagina(self):
        categorias = {c.category for c in detect_in_text(f"Titular: {CPF_VALIDO}")}

        assert CategoryType.cpf in categorias

    def test_ignora_sequencia_de_11_digitos_que_nao_e_cpf(self):
        """Código de pedido não pode virar achado de risco alto."""
        categorias = {c.category for c in detect_in_text("Pedido 12345678901 confirmado")}

        assert CategoryType.cpf not in categorias

    @pytest.mark.parametrize(
        "telefone",
        ["(11) 98765-4321", "11987654321", "+55 11 98765-4321", "(11) 3456-7890"],
    )
    def test_detecta_telefone_em_formatos_variados(self, telefone):
        categorias = {c.category for c in detect_in_text(f"Ligue {telefone}")}

        assert CategoryType.phone in categorias

    def test_detecta_email_e_cep(self):
        texto = "Contato: vendas@empresa.com.br - CEP 01310-100"

        categorias = {c.category for c in detect_in_text(texto)}

        assert categorias == {CategoryType.email, CategoryType.address}

    def test_cpf_nao_e_contado_tambem_como_telefone(self):
        """CPF e celular têm 11 dígitos; sem desambiguar, um CPF viraria dois achados."""
        categorias = {c.category for c in detect_in_text(f"CPF {CPF_VALIDO_SEM_MASCARA}")}

        assert categorias == {CategoryType.cpf}

    def test_nao_reporta_a_mesma_categoria_duas_vezes(self):
        texto = "a@b.com.br e c@d.com.br"

        assert len(detect_in_text(texto)) == 1

    def test_texto_sem_dado_pessoal_nao_gera_achado(self):
        assert detect_in_text("Bem-vindo à nossa loja de ferramentas.") == []
