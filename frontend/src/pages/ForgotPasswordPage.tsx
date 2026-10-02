import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../lib/useAuth';
import { AuthCard } from '../components/ui/AuthCard';
import { TextField } from '../components/ui/TextField';
import { Button } from '../components/ui/Button';

export function ForgotPasswordPage() {
  const { sendPasswordResetEmail } = useAuth();
  const [email, setEmail] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [enviado, setEnviado] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await sendPasswordResetEmail(email);
      setEnviado(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível enviar o e-mail.');
    } finally {
      setEnviando(false);
    }
  }

  if (enviado) {
    return (
      <AuthCard>
        <div className="flex flex-col gap-4">
          <h1 className="text-xl font-semibold">Verifique seu e-mail</h1>
          <p className="text-sm text-text-muted">
            Se houver uma conta para <strong className="text-text">{email}</strong>, enviamos um
            link para redefinir a senha.
          </p>
          <Link to="/login" className="text-sm text-primary hover:underline">
            Voltar para o login
          </Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard>
      <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold">Esqueci minha senha</h1>
          <p className="mt-1 text-sm text-text-muted">
            Informe seu e-mail e enviaremos um link para redefinir a senha.
          </p>
        </div>

        <TextField
          id="email"
          label="E-mail"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        {erro && (
          <p role="alert" className="text-sm text-danger">
            {erro}
          </p>
        )}

        <Button type="submit" disabled={enviando}>
          {enviando ? 'Enviando...' : 'Enviar link'}
        </Button>

        <Link to="/login" className="text-sm text-primary hover:underline">
          Voltar para o login
        </Link>
      </form>
    </AuthCard>
  );
}
