"""Testes contra resolução DNS real — sem isso não dá para provar que a
checagem funciona (o objetivo é justamente resolver o hostname e olhar o IP).
Usa domínios/IPs públicos conhecidos e reservados pela IANA, nunca hosts de
terceiros que exijam resposta HTTP real."""

from app.scanner.ssrf_guard import is_safe_url


class TestEsquemaEHost:
    def test_rejeita_esquema_nao_http(self):
        assert is_safe_url("file:///etc/passwd") is False
        assert is_safe_url("ftp://exemplo.com") is False

    def test_rejeita_url_sem_host(self):
        assert is_safe_url("http://") is False


class TestIpsBloqueados:
    def test_rejeita_loopback(self):
        assert is_safe_url("http://127.0.0.1") is False
        assert is_safe_url("http://[::1]") is False

    def test_rejeita_link_local_incluindo_metadados_de_nuvem(self):
        assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    def test_rejeita_rede_privada(self):
        assert is_safe_url("http://192.168.1.1") is False
        assert is_safe_url("http://10.0.0.1") is False
        assert is_safe_url("http://172.16.0.1") is False

    def test_rejeita_hostname_que_resolve_para_localhost(self):
        assert is_safe_url("http://localhost") is False

    def test_rejeita_hostname_inexistente(self):
        assert is_safe_url("http://este-dominio-nao-existe-de-verdade-12345.invalid") is False


class TestIpsPermitidos:
    def test_aceita_ip_publico_direto(self):
        # 8.8.8.8 é o resolvedor DNS público do Google — endereço público estável.
        assert is_safe_url("http://8.8.8.8") is True

    def test_aceita_dominio_publico_conhecido(self):
        assert is_safe_url("https://example.com") is True
