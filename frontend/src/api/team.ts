import { apiFetch } from './client';
import type { TeamInviteCreate, User } from '../types/api';

export function listTeamMembers(): Promise<User[]> {
  return apiFetch<User[]>('/team/members');
}

export function inviteTeamMember(data: TeamInviteCreate): Promise<User> {
  return apiFetch<User>('/team/invitations', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function removeTeamMember(userId: string): Promise<void> {
  return apiFetch<void>(`/team/members/${userId}`, { method: 'DELETE' });
}
