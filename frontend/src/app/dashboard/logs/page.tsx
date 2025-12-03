'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ScrollText, 
  Filter,
  Calendar,
  User,
  Building2,
  Layers,
  Settings,
  RefreshCw,
  Shield
} from 'lucide-react';
import { getToken, getUser } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Log {
  id: number;
  admin_id: number;
  admin_email: string;
  action: string;
  target_type: string;
  target_id: number | null;
  target_name: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

interface LogStats {
  period_days: number;
  total: number;
  by_action: Record<string, number>;
  by_target: Record<string, number>;
  by_admin: Record<string, number>;
}

const actionLabels: Record<string, string> = {
  create_tenant: 'Criar Cliente',
  update_tenant: 'Atualizar Cliente',
  delete_tenant: 'Deletar Cliente',
  create_niche: 'Criar Nicho',
  update_niche: 'Atualizar Nicho',
  delete_niche: 'Deletar Nicho',
  seed_niches: 'Popular Nichos',
  login: 'Login',
  login_failed: 'Login Falhou',
};

const targetIcons: Record<string, typeof Building2> = {
  tenant: Building2,
  niche: Layers,
  settings: Settings,
  user: User,
};

export default function LogsPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<Log[]>([]);
  const [stats, setStats] = useState<LogStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    const user = getUser();
    if (user?.role !== 'superadmin') {
      router.push('/dashboard');
      return;
    }
    fetchData();
  }, [router, days, actionFilter]);

  async function fetchData() {
    setLoading(true);
    await Promise.all([fetchLogs(), fetchStats()]);
    setLoading(false);
  }

  async function fetchLogs() {
    try {
      const token = getToken();
      const params = new URLSearchParams({ days: days.toString() });
      if (actionFilter) params.set('action', actionFilter);

      const response = await fetch(`${API_URL}/admin/logs?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs);
      }
    } catch (err) {
      console.error('Erro ao carregar logs:', err);
    }
  }

  async function fetchStats() {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/logs/stats?days=${days}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Erro ao carregar stats:', err);
    }
  }

  function formatDate(dateString: string) {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function getActionColor(action: string) {
    if (action.includes('create')) return 'text-green-600 bg-green-50';
    if (action.includes('update')) return 'text-blue-600 bg-blue-50';
    if (action.includes('delete')) return 'text-red-600 bg-red-50';
    if (action.includes('login')) return 'text-purple-600 bg-purple-50';
    return 'text-gray-600 bg-gray-50';
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Logs de Auditoria</h1>
          <p className="text-gray-600">Histórico de ações administrativas</p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg transition-colors"
        >
          <RefreshCw className="w-5 h-5" />
          Atualizar
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <p className="text-gray-500 text-sm">Total de Ações</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            <p className="text-gray-400 text-sm">últimos {days} dias</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <p className="text-gray-500 text-sm">Por Tipo</p>
            <div className="mt-2 space-y-1">
              {Object.entries(stats.by_target).slice(0, 3).map(([type, count]) => (
                <div key={type} className="flex justify-between text-sm">
                  <span className="text-gray-600 capitalize">{type}</span>
                  <span className="text-purple-600 font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <p className="text-gray-500 text-sm">Por Ação</p>
            <div className="mt-2 space-y-1">
              {Object.entries(stats.by_action).slice(0, 3).map(([action, count]) => (
                <div key={action} className="flex justify-between text-sm">
                  <span className="text-gray-600">{actionLabels[action] || action}</span>
                  <span className="text-purple-600 font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <p className="text-gray-500 text-sm">Por Admin</p>
            <div className="mt-2 space-y-1">
              {Object.entries(stats.by_admin).slice(0, 3).map(([admin, count]) => (
                <div key={admin} className="flex justify-between text-sm">
                  <span className="text-gray-600 truncate max-w-[140px]">{admin}</span>
                  <span className="text-purple-600 font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 items-center bg-white p-4 rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-gray-400" />
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
            <option value={365}>Último ano</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">Todas as ações</option>
            <option value="create_tenant">Criar Cliente</option>
            <option value="update_tenant">Atualizar Cliente</option>
            <option value="delete_tenant">Deletar Cliente</option>
            <option value="create_niche">Criar Nicho</option>
            <option value="update_niche">Atualizar Nicho</option>
            <option value="seed_niches">Popular Nichos</option>
          </select>
        </div>
      </div>

      {/* Logs List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Carregando...</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">Nenhum log encontrado</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {logs.map((log) => {
              const TargetIcon = targetIcons[log.target_type] || ScrollText;
              return (
                <div key={log.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <TargetIcon className="w-5 h-5 text-gray-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getActionColor(log.action)}`}>
                          {actionLabels[log.action] || log.action}
                        </span>
                        {log.target_name && (
                          <span className="text-gray-900 font-medium">{log.target_name}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <User className="w-4 h-4" />
                          {log.admin_email}
                        </span>
                        <span>{formatDate(log.created_at)}</span>
                        {log.ip_address && (
                          <span className="text-gray-400">IP: {log.ip_address}</span>
                        )}
                      </div>
                      {log.details && Object.keys(log.details).length > 0 && (
                        <details className="mt-2">
                          <summary className="text-xs text-purple-600 cursor-pointer hover:underline">
                            Ver detalhes
                          </summary>
                          <div className="mt-1 text-xs text-gray-500 bg-gray-50 rounded p-2 font-mono overflow-x-auto">
                            {JSON.stringify(log.details, null, 2)}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}