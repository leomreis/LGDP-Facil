import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './lib/AuthContext';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { OnboardingGate } from './components/layout/OnboardingGate';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/LoginPage';
import { SignUpPage } from './pages/SignUpPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { ScansListPage } from './pages/ScansListPage';
import { ScanDetailPage } from './pages/ScanDetailPage';
import { PoliciesPage } from './pages/PoliciesPage';
import { TeamPage } from './pages/TeamPage';
import { PublicPolicyPage } from './pages/PublicPolicyPage';

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/cadastro" element={<SignUpPage />} />
        <Route path="/esqueci-senha" element={<ForgotPasswordPage />} />
        <Route path="/redefinir-senha" element={<ResetPasswordPage />} />
        <Route path="/p/:companyId/:slug" element={<PublicPolicyPage />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/onboarding" element={<OnboardingPage />} />

          <Route element={<OnboardingGate />}>
            <Route element={<AppShell />}>
              <Route path="/scans" element={<ScansListPage />} />
              <Route path="/scans/:scanId" element={<ScanDetailPage />} />
              <Route path="/policies" element={<PoliciesPage />} />
              <Route path="/team" element={<TeamPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="/" element={<Navigate to="/scans" replace />} />
        <Route path="*" element={<Navigate to="/scans" replace />} />
      </Routes>
    </AuthProvider>
  );
}
