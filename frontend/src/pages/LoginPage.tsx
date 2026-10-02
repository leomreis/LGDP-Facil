import { useState, type FormEvent } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../lib/useAuth';
import { AuthCard } from '../components/ui/AuthCard';
import { TextField } from '../components/ui/TextField';
import { Button } from '../components/ui/Button';

export function LoginPage() {
  const { session, signInWithPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (session) {
    return <Navigate to="/scans" replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await signInWithPassword(email, password);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível entrar.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthCard>
      <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold">Entrar</h1>

        <TextField
          id="email"
          label="E-mail"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <TextField
          id="password"
          label="Senha"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        {erro && (
          <p role="alert" className="text-sm text-danger">
            {erro}
          </p>
        )}

        <Button type="submit" disabled={enviando}>
          {enviando ? 'Entrando...' : 'Entrar'}
        </Button>

        <Link to="/esqueci-senha" className="text-sm text-primary hover:underline">
          Esqueci minha senha
        </Link>

        <p className="text-sm text-text-muted">
          Ainda não tem conta?{' '}
          <Link to="/cadastro" className="text-primary hover:underline">
            Criar conta
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
