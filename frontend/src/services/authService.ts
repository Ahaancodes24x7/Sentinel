import { apiRequest } from '../api/client';
import type { User, UserRole } from '../types/sentinel';

const DEMO_USERS: Record<string, User> = {
  hse_manager: {
    username: 'hse_manager_demo',
    name: 'Dr. Alistair Vance',
    role: 'hse_manager',
    organization: 'Shell Global HSE Operations',
    site: 'North Refinery',
    avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
  },
  hse_analyst: {
    username: 'hse_analyst_demo',
    name: 'Elena Rostova',
    role: 'hse_analyst',
    organization: 'ExxonMobil Upstream Analytics',
    site: 'Rig 4',
    avatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80',
  },
  hse_reviewer: {
    username: 'hse_reviewer_demo',
    name: 'Marcus Thorne',
    role: 'hse_reviewer',
    organization: 'BP Safety Review Center',
    site: 'Processing Unit 4',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
  },
  auditor: {
    username: 'auditor_demo',
    name: 'Sarah Jenkins',
    role: 'auditor',
    organization: 'ONGC Safety Oversight Board',
    site: 'All Sites',
    avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
  },
};

export const authService = {
  getCurrentUser(): User {
    const savedRole = (localStorage.getItem('sentinel_role') as UserRole) || 'hse_manager';
    return DEMO_USERS[savedRole] || DEMO_USERS.hse_manager;
  },

  setRole(role: UserRole): User {
    localStorage.setItem('sentinel_role', role);
    localStorage.setItem('sentinel_token', `demo_token_${role}_${Date.now()}`);
    return DEMO_USERS[role] || DEMO_USERS.hse_manager;
  },

  async login(username: string, role: UserRole = 'hse_manager'): Promise<{ user: User; token: string }> {
    const { data } = await apiRequest<{ access_token: string; role: UserRole }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password: 'demo' }),
    });

    const activeRole = data?.role || role;
    const user = this.setRole(activeRole);
    return {
      user,
      token: data?.access_token || `demo_token_${activeRole}`,
    };
  },

  logout() {
    localStorage.removeItem('sentinel_token');
    localStorage.removeItem('sentinel_role');
  },
};
