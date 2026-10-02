import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/useAuth';
import { AuthCard } from '../components/ui/AuthCard';
import { TextField } from '../components/ui/TextField';
import { Button } from '../components/ui/Button';

/**
 * Página de destino do link de "esqueci minha senha". O Supabase já autentica
 * a sessão de recuperação a partir do token na URL antes desta página montar
 * (detectSessionInUrl, padrão do supabase-js) — aqui só falta pedir a senha
 * nova e chamar updateUser.
 */
export function ResetPasswordPage() {
  const { updatePassword } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErro(null);

    if (password !== confirmacao) {
      setErro('As senhas não coincidem.');
      return;
    }

    setEnviando(true);
    try {
      await updatePassword(password);
      navigate('/scans', { replace: true });
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível redefinir a senha.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthCard>
      <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold">Definir nova senha</h1>

        <TextField
          id="password"
          label="Nova senha"
          type="password"
          minLength={6}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <TextField
          id="confirmacao"
          label="Confirme a nova senha"
          type="password"
          minLength={6}
          value={confirmacao}
          onChange={(event) => setConfirmacao(event.target.value)}
          required
        />

        {erro && (
          <p role="alert" className="text-sm text-danger">
            {erro}
          </p>
        )}

        <Button type="submit" disabled={enviando}>
          {enviando ? 'Salvando...' : 'Salvar nova senha'}
        </Button>
      </form>
    </AuthCard>
  );
}
