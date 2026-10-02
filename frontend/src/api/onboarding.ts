import { apiFetch } from './client';
import type { OnboardingCreate, OnboardingResponse } from '../types/api';

export function completeOnboarding(data: OnboardingCreate): Promise<OnboardingResponse> {
  return apiFetch<OnboardingResponse>('/onboarding', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
