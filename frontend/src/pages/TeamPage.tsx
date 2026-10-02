import { useEffect, useState, type FormEvent } from 'react';
import { getMe } from '../api/users';
import { inviteTeamMember, listTeamMembers, removeTeamMember } from '../api/team';
import type { User } from '../types/api';
import { TextField } from '../components/ui/TextField';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export function TeamPage() {
  const [membros, setMembros] = useState<User[] | null>(null);
  const [euMesmo, setEuMesmo] = useState<User | null>(null);
  const [email, setEmail] = useState('');
  const [nome, setNome] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);

  async function carregar() {
    const [lista, eu] = await Promise.all([listTeamMembers(), getMe()]);
    setMembros(lista);
    setEuMesmo(eu);
  }

  useEffect(() => {
    carregar().catch((e) => setErro(e instanceof Error ? e.message : 'Erro ao carregar a equipe.'));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErro(null);
    setSucesso(null);
    setEnviando(true);
    try {
      await inviteTeamMember({ email, name: nome });
      setSucesso(`Convite enviado para ${email}.`);
      setEmail('');
      setNome('');
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível enviar o convite.');
    } finally {
      setEnviando(false);
    }
  }

  const souOwner = euMesmo?.role === 'owner';

  async function remover(membro: User) {
    if (!window.confirm(`Remover ${membro.name} da equipe?`)) return;
    setErro(null);
    try {
      await removeTeamMember(membro.id);
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível remover o membro.');
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Equipe</h1>

      {souOwner && (
        <form onSubmit={(event) => void handleSubmit(event)} className="mb-8 flex items-end gap-2">
          <TextField
            id="invite-name"
            label="Nome"
            value={nome}
            onChange={(event) => setNome(event.target.value)}
            required
          />
          <TextField
            id="invite-email"
            label="E-mail"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <Button type="submit" disabled={enviando}>
            {enviando ? 'Convidando...' : 'Convidar'}
          </Button>
        </form>
      )}

      {erro && <p className="mb-4 text-sm text-danger">{erro}</p>}
      {sucesso && <p className="mb-4 text-sm text-risk-low">{sucesso}</p>}

      {membros === null && <p className="text-text-muted">Carregando...</p>}

      <ul className="flex flex-col gap-2">
        {membros?.map((membro) => (
          <li
            key={membro.id}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3"
          >
            <div className="flex-1">
              <p className="font-medium">{membro.name}</p>
              <p className="text-sm text-text-muted">{membro.email}</p>
            </div>
            <Badge tone={membro.role === 'owner' ? 'success' : 'neutral'}>
              {membro.role === 'owner' ? 'Dono' : 'Membro'}
            </Badge>
            {souOwner && membro.id !== euMesmo?.id && (
              <Button variant="secondary" type="button" onClick={() => void remover(membro)}>
                Remover
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
