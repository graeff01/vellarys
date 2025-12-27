import { getToken } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  reference_type: string | null;
  reference_id: number | null;
  read: boolean;
  created_at: string;
}

export async function getNotifications(unreadOnly: boolean = false): Promise<Notification[]> {
  const token = getToken();
  const params = unreadOnly ? '?unread_only=true' : '';
  
  const response = await fetch(`${API_URL}/notifications${params}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar notificações');
  }

  return response.json();
}

export async function getUnreadCount(): Promise<number> {
  const token = getToken();
  
  const response = await fetch(`${API_URL}/notifications/count`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    return 0;
  }

  const data = await response.json();
  return data.unread_count || data.count || 0;
}

export async function markAsRead(notificationId: number): Promise<void> {
  const token = getToken();
  
  await fetch(`${API_URL}/notifications/${notificationId}/read`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
}

export async function markAllAsRead(): Promise<void> {
  const token = getToken();
  
  await fetch(`${API_URL}/notifications/read-all`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
}