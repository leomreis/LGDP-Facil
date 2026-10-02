import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/useAuth';
import { AuthCard } from '../components/ui/AuthCard';
import { TextField } from '../components/ui/TextField';
import { Button } from '../components/ui/Button';

export function SignUpPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [contaCriada, setContaCriada] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await signUp(email, password);
      setContaCriada(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível criar a conta.');
    } finally {
      setEnviando(false);
    }
  }

  if (contaCriada) {
    return (
      <AuthCard>
        <div className="flex flex-col gap-4">
          <h1 className="text-xl font-semibold">Confirme seu e-mail</h1>
          <p className="text-sm text-text-muted">
            Enviamos um link de confirmação para <strong className="text-text">{email}</strong>.
            Confirme para poder entrar.
          </p>
          <Button type="button" onClick={() => navigate('/login')}>
            Ir para o login
          </Button>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard>
      <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold">Criar conta</h1>

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
          minLength={6}
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
          {enviando ? 'Criando...' : 'Criar conta'}
        </Button>

        <p className="text-sm text-text-muted">
          Já tem conta?{' '}
          <Link to="/login" className="text-primary hover:underline">
            Entrar
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
