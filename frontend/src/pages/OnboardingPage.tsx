import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { completeOnboarding } from '../api/onboarding';
import { ApiError } from '../api/client';
import { AuthCard } from '../components/ui/AuthCard';
import { TextField } from '../components/ui/TextField';
import { Button } from '../components/ui/Button';

export function OnboardingPage() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [siteUrl, setSiteUrl] = useState('');
  const [userName, setUserName] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await completeOnboarding({
        company_name: companyName,
        cnpj,
        site_url: siteUrl || null,
        user_name: userName,
      });
      navigate('/scans', { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        navigate('/scans', { replace: true });
        return;
      }
      setErro(e instanceof Error ? e.message : 'Não foi possível concluir o cadastro.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthCard>
      <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold">Cadastre sua empresa</h1>
          <p className="mt-1 text-sm text-text-muted">
            Último passo antes de rodar seu primeiro scan de conformidade.
          </p>
        </div>

        <TextField
          id="userName"
          label="Seu nome"
          value={userName}
          onChange={(event) => setUserName(event.target.value)}
          required
        />
        <TextField
          id="companyName"
          label="Nome da empresa"
          value={companyName}
          onChange={(event) => setCompanyName(event.target.value)}
          required
        />
        <TextField
          id="cnpj"
          label="CNPJ"
          value={cnpj}
          onChange={(event) => setCnpj(event.target.value)}
          placeholder="00000000000000"
          required
        />
        <TextField
          id="siteUrl"
          label="Site da empresa (opcional)"
          type="url"
          value={siteUrl}
          onChange={(event) => setSiteUrl(event.target.value)}
          placeholder="https://minhaempresa.com.br"
        />

        {erro && (
          <p role="alert" className="text-sm text-danger">
            {erro}
          </p>
        )}

        <Button type="submit" disabled={enviando}>
          {enviando ? 'Salvando...' : 'Concluir cadastro'}
        </Button>
      </form>
    </AuthCard>
  );
}
