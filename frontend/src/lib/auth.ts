const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  tenant: {
    id: number;
    name: string;
    slug: string;
  } | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao fazer login');
  }

  return response.json();
}

export async function getMe(token: string): Promise<User> {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Não autorizado');
  }

  return response.json();
}

// Salva token no localStorage
export function saveToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('velaris_token', token);
  }
}

// Recupera token
export function getToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('velaris_token');
  }
  return null;
}

// Remove token (logout)
export function removeToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('velaris_token');
  }
}

// Salva dados do usuário
export function saveUser(user: User) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('velaris_user', JSON.stringify(user));
  }
}

// Recupera dados do usuário
export function getUser(): User | null {
  if (typeof window !== 'undefined') {
    const data = localStorage.getItem('velaris_user');
    return data ? JSON.parse(data) : null;
  }
  return null;
}

// Remove dados do usuário
export function removeUser() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('velaris_user');
  }
}

// Logout completo
export function logout() {
  removeToken();
  removeUser();
}