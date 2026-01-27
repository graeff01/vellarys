'use client';

import { useState, useEffect, Suspense } from 'react';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { getToken, getUser } from '@/lib/auth';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Calendar, MessageSquare, StickyNote, Paperclip, Zap, Search,
  BarChart3, Archive, Mic, Shield, RefreshCw, Brain, Save, Loader2,
  UserCheck, HeartPulse, EyeOff, Lock, Users, Bell, ChevronDown, CheckCircle2,
  Bot, Rocket, Sparkles, CreditCard, RotateCcw, AlertCircle
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Feature {
  key: string;
  name: string;
  description: string;
  icon: any;
  category: 'core' | 'advanced' | 'security' | 'experimental';
  comingSoon?: boolean;
}

const FEATURES: Feature[] = [
  // Core Features
  { key: 'calendar_enabled', name: 'Calendário de Agendamentos', description: 'Permite vendedores agendarem visitas com leads', icon: Calendar, category: 'core' },
  { key: 'templates_enabled', name: 'Templates de Resposta', description: 'Mensagens pré-definidas com variáveis dinâmicas', icon: MessageSquare, category: 'core' },
  { key: 'notes_enabled', name: 'Anotações Internas', description: 'Notas privadas da equipe sobre leads', icon: StickyNote, category: 'core' },
  { key: 'attachments_enabled', name: 'Upload de Anexos', description: 'Envio de imagens, PDFs e documentos', icon: Paperclip, category: 'core' },

  // Advanced Features
  { key: 'sse_enabled', name: 'Atualizações em Tempo Real', description: 'Mensagens aparecem instantaneamente (SSE)', icon: Zap, category: 'advanced' },
  { key: 'search_enabled', name: 'Busca de Mensagens', description: 'Full-text search em todo histórico', icon: Search, category: 'advanced' },
  { key: 'metrics_enabled', name: 'Métricas e Analytics', description: 'Dashboards com KPIs e performance', icon: BarChart3, category: 'advanced' },
  { key: 'archive_enabled', name: 'Arquivamento de Leads', description: 'Organização de leads inativos', icon: Archive, category: 'advanced' },
  { key: 'voice_response_enabled', name: 'Respostas em Áudio', description: 'IA responde com mensagens de voz', icon: Mic, category: 'advanced' },
  { key: 'ai_auto_handoff_enabled', name: 'Auto-Transferência (IA)', description: 'Transfere para o vendedor assim que qualificado', icon: UserCheck, category: 'advanced' },
  { key: 'ai_sentiment_alerts_enabled', name: 'Alertas de Sentimento', description: 'Monitora humor e urgência dos leads (IA)', icon: HeartPulse, category: 'advanced' },

  // Security Features
  { key: 'security_ghost_mode_enabled', name: 'Modo Privacidade', description: 'Oculta telefone dos leads para os vendedores', icon: EyeOff, category: 'security' },
  { key: 'security_export_lock_enabled', name: 'Trava de Exportação', description: 'Apenas Admins Master podem baixar dados', icon: Lock, category: 'security' },
  { key: 'distrib_auto_assign_enabled', name: 'Atribuição Inteligente', description: 'Distribuição automática ativada globalmente', icon: Users, category: 'security' },

  // Experimental Features
  { key: 'ai_guard_enabled', name: 'Guardrails Avançados', description: 'Proteções de preço, concorrentes, etc', icon: Shield, category: 'experimental' },
  { key: 'reengagement_enabled', name: 'Re-engajamento Automático', description: 'Follow-ups automáticos para leads inativos', icon: RefreshCw, category: 'experimental' },
  { key: 'knowledge_base_enabled', name: 'Base de Conhecimento (RAG)', description: 'IA busca respostas em documentos', icon: Brain, category: 'experimental', comingSoon: true },
];

const PLANS = [
  { id: 'starter', name: 'Starter', color: 'bg-blue-100 text-blue-700' },
  { id: 'premium', name: 'Premium', color: 'bg-purple-100 text-purple-700' },
  { id: 'enterprise', name: 'Enterprise', color: 'bg-indigo-100 text-indigo-700' }
];

export default function ControlCenterPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>}>
      <ControlCenterContent />
    </Suspense>
  );
}

function ControlCenterContent() {
  const [planFeatures, setPlanFeatures] = useState<Record<string, boolean>>({});
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const [finalFeatures, setFinalFeatures] = useState<Record<string, boolean>>({});

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [availableTenants, setAvailableTenants] = useState<any[]>([]);
  const [currentTenant, setCurrentTenant] = useState<any>(null);

  const searchParams = useSearchParams();
  const router = useRouter();
  const { toast } = useToast();

  const targetTenantId = searchParams.get('target_tenant_id');

  // Inicialização: Checa SuperAdmin e busca lista de clientes uma só vez
  useEffect(() => {
    const user = getUser();
    const isSuper = user?.role === 'superadmin' || !!user?.is_superadmin;
    setIsSuperAdmin(isSuper);

    if (isSuper) {
      fetchTenants();
    }
  }, []);

  // Carrega as features sempre que o cliente selecionado mudar
  useEffect(() => {
    loadFeatures();
  }, [targetTenantId]);

  async function fetchTenants() {
    try {
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');
      const apiUrl = `${baseUrl}/v1`;
      const token = getToken();
      const response = await fetch(`${apiUrl}/admin/tenants?limit=100`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableTenants(data.tenants || []);
      }
    } catch (error) {
      console.error('Erro ao carregar clientes:', error);
    }
  }

  async function loadFeatures() {
    try {
      setLoading(true);
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');
      const apiUrl = `${baseUrl}/v1`;
      const token = getToken();

      let url = `${apiUrl}/settings/features`;
      if (targetTenantId) url += `?target_tenant_id=${targetTenantId}`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-Tenant-Override': targetTenantId || ''
        },
      });

      if (!response.ok) throw new Error('Erro ao carregar features');

      const data = await response.json();

      // Nova estrutura vinda do backend
      setPlanFeatures(data.plan_features || {});
      setOverrides(data.overrides || {});
      setFinalFeatures(data.final_features || data); // Fallback para compatibilidade

      // Busca dados do tenant atual se estiver selecionado
      if (targetTenantId && availableTenants.length > 0) {
        const t = availableTenants.find(x => x.id.toString() === targetTenantId);
        if (t) setCurrentTenant(t);
      }
    } catch (err) {
      console.error('❌ Erro:', err);
      toast({ variant: 'destructive', title: 'Erro de conexão', description: 'Não foi possível carregar as configurações.' });
    } finally {
      setLoading(false);
    }
  }

  const handleTenantChange = (id: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (id) params.set('target_tenant_id', id);
    else params.delete('target_tenant_id');
    router.push(`/dashboard/control-center?${params.toString()}`);
  };

  async function handlePlanChange(planId: string) {
    if (!targetTenantId) return;
    try {
      setSaving(true);
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');
      const apiUrl = `${baseUrl}/v1`;
      const token = getToken();

      const response = await fetch(`${apiUrl}/admin/tenants/${targetTenantId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ plan: planId }),
      });

      if (!response.ok) throw new Error('Erro ao atualizar plano');

      toast({ title: 'Plano Alterado!', description: `O cliente agora está no nível ${planId.toUpperCase()}.` });

      // Atualiza o objeto do tenant localmente para o nome do plano mudar no UI
      setCurrentTenant((prev: any) => ({ ...prev, plan: planId }));

      // Recarrega features para ver a nova base do plano
      loadFeatures();
    } catch (err: any) {
      toast({ variant: 'destructive', title: 'Falha na atualização', description: err.message });
    } finally {
      setSaving(false);
    }
  }

  async function handleToggle(key: string, enabled: boolean) {
    const newOverrides = { ...overrides, [key]: enabled };
    setOverrides(newOverrides);
    setFinalFeatures({ ...planFeatures, ...newOverrides });

    // Auto-save corporativo: Salva ao trocar para ser mais ágil, ou você prefere botão?
    // Vou colocar botão de salvar aqui para evitar chamadas excessivas, mas com feedback visual.
  }

  async function saveOverrides(targetOverrides: any = overrides) {
    try {
      setSaving(true);
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');
      const apiUrl = `${baseUrl}/v1`;
      const token = getToken();

      let url = `${apiUrl}/settings/features`;
      if (targetTenantId) url += `?target_tenant_id=${targetTenantId}`;

      const response = await fetch(url, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Tenant-Override': targetTenantId || ''
        },
        body: JSON.stringify(targetOverrides),
      });

      if (!response.ok) throw new Error('Erro ao salvar');

      toast({ title: 'Configurações Salvas', description: 'Permissões do cliente atualizadas.' });
      loadFeatures(); // Refresh para garantir consistência
    } catch (err: any) {
      toast({ variant: 'destructive', title: 'Erro ao salvar', description: err.message });
    } finally {
      setSaving(false);
    }
  }

  async function resetToDefaults() {
    // Limpa todos os overrides enviando um objeto vazio (o backend vai deletar as chaves no MutableDict)
    // Nota: Dependendo da implementação do backend, podemos precisar enviar as chaves como nulas ou deletar.
    // Vou assumir que enviar um objeto que não sobrescreve nada reseta o Merge.
    await saveOverrides({});
    setOverrides({});
    toast({ title: 'Resetado!', description: 'Voltamos para as configurações padrão do plano.' });
  }

  const sections = [
    { title: 'Core Business', badge: 'Essenciais', category: 'core', color: 'bg-blue-100 text-blue-700' },
    { title: 'AI & Intelligence', badge: 'Premium', category: 'advanced', color: 'bg-purple-100 text-purple-700' },
    { title: 'Governance & Security', badge: 'Segurança', category: 'security', color: 'bg-emerald-100 text-emerald-700' },
    { title: 'Future Labs', badge: 'Experimental', category: 'experimental', color: 'bg-orange-100 text-orange-700' }
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">

      {/* 🚀 Master Navigation Bar */}
      {isSuperAdmin && (
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-4 bg-white p-2 rounded-2xl border border-gray-200 shadow-xl overflow-hidden">
          <div className="flex items-center gap-3 px-4 py-2 bg-slate-50 rounded-xl border border-slate-100 min-w-[300px]">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center text-white">
              <Users className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none mb-1">Cliente Selecionado</p>
              <h3 className="font-bold text-slate-900 truncate">
                {currentTenant?.name || 'Selecione um Cliente...'}
              </h3>
            </div>
          </div>

          <div className="flex-1 flex items-center gap-2 px-2 overflow-x-auto no-scrollbar">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold">
                  Trocar Unidade
                  <ChevronDown className="w-4 h-4 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-[300px] p-2 rounded-2xl shadow-2xl border-slate-100">
                <DropdownMenuLabel className="text-xs text-slate-400 uppercase">Seus Clientes Ativos</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <div className="max-h-[400px] overflow-y-auto pr-1">
                  <DropdownMenuItem onClick={() => handleTenantChange('')} className="rounded-xl p-3 cursor-pointer">
                    Meu Próprio Plano (Default)
                  </DropdownMenuItem>
                  {availableTenants.map(t => (
                    <DropdownMenuItem
                      key={t.id}
                      onClick={() => handleTenantChange(t.id.toString())}
                      className={`rounded-xl p-3 cursor-pointer flex items-center justify-between ${targetTenantId === t.id.toString() ? 'bg-indigo-50' : ''}`}
                    >
                      <div className="flex flex-col">
                        <span className="font-bold text-slate-900">{t.name}</span>
                        <span className="text-[10px] text-slate-400">Plano: {t.plan?.toUpperCase()}</span>
                      </div>
                      {targetTenantId === t.id.toString() && <CheckCircle2 className="w-4 h-4 text-indigo-600" />}
                    </DropdownMenuItem>
                  ))}
                </div>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {targetTenantId && (
            <div className="flex items-center gap-2 p-1 bg-slate-50 rounded-xl border border-slate-100 mr-2">
              {PLANS.map(p => (
                <button
                  key={p.id}
                  onClick={() => handlePlanChange(p.id)}
                  disabled={saving}
                  className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${currentTenant?.plan === p.id ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200' : 'text-slate-400 hover:text-slate-600'}`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 🎫 Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-black text-slate-900 tracking-tight">Centro de Provisionamento</h1>
            <Badge className="bg-amber-100 text-amber-700 border-none font-black px-3 py-1">MASTER MODE</Badge>
          </div>
          <p className="text-slate-500 max-w-2xl font-medium leading-relaxed">
            Defina o que está ativo na conta do cliente. Funcionalidades marcadas como <span className="text-indigo-600 font-bold underline decoration-indigo-200">sobrescritas</span> ignoram a base do plano contratado.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={resetToDefaults}
            disabled={loading || saving || !targetTenantId}
            className="rounded-2xl border-slate-200 h-12 px-6 gap-2 text-slate-600 font-bold hover:bg-slate-50"
          >
            <RotateCcw className="w-4 h-4" />
            Resetar Plano
          </Button>
          <Button
            onClick={() => saveOverrides()}
            disabled={loading || saving || !targetTenantId}
            className="rounded-2xl bg-indigo-600 hover:bg-indigo-700 h-12 px-8 gap-2 font-bold shadow-lg shadow-indigo-100"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Salvar Provisionamento
          </Button>
        </div>
      </div>

      {/* ⚠️ Warning if no tenant selected */}
      {!targetTenantId && isSuperAdmin && (
        <div className="bg-amber-50 border border-amber-100 p-6 rounded-3xl flex items-center gap-4 text-amber-800">
          <AlertCircle className="w-8 h-8 flex-shrink-0" />
          <div>
            <p className="font-bold">Modo de Visualização Própria</p>
            <p className="text-sm opacity-80">Você está vendo as configurações da conta Admin. Selecione um cliente no menu superior para provisionar acessos de terceiros.</p>
          </div>
        </div>
      )}

      {/* 🧩 Features Grid */}
      <div className="space-y-12 pb-20">
        {sections.map(section => (
          <div key={section.category} className="space-y-6">
            <div className="flex items-center gap-4 overflow-hidden">
              <h2 className="text-xl font-black text-slate-800 whitespace-nowrap">{section.title}</h2>
              <div className="h-px bg-slate-100 flex-1" />
              <Badge className={`${section.color} border-none font-bold`}>{section.badge}</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {FEATURES.filter(f => f.category === section.category).map(f => {
                const isOverridden = overrides.hasOwnProperty(f.key);
                const isEnabled = finalFeatures[f.key] ?? false;
                const planValue = planFeatures[f.key] ?? false;

                return (
                  <Card
                    key={f.key}
                    className={`relative group p-6 rounded-3xl transition-all duration-300 border-2 overflow-hidden ${isEnabled ? 'border-indigo-500 bg-white shadow-xl shadow-indigo-50/50' : 'border-slate-50 bg-slate-50/50 opacity-70 hover:opacity-100'}`}
                  >
                    <div className="flex flex-col gap-4 h-full">
                      <div className="flex items-start justify-between">
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-colors ${isEnabled ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200' : 'bg-white text-slate-300 border border-slate-100'}`}>
                          <f.icon className="w-6 h-6" />
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <Switch
                            checked={isEnabled}
                            onCheckedChange={(val) => handleToggle(f.key, val)}
                            disabled={loading || f.comingSoon || !targetTenantId}
                            className="data-[state=checked]:bg-indigo-600"
                          />
                          {isOverridden && (
                            <span className="text-[9px] font-black text-indigo-600 uppercase tracking-tighter">Override</span>
                          )}
                        </div>
                      </div>

                      <div className="space-y-1">
                        <h3 className="font-bold text-slate-900 leading-none flex items-center gap-2">
                          {f.name}
                          {f.comingSoon && <span className="text-[10px] bg-slate-200 px-1.5 rounded uppercase">Em Breve</span>}
                        </h3>
                        <p className="text-xs text-slate-500 font-medium leading-relaxed">{f.description}</p>
                      </div>

                      <div className="mt-auto pt-4 flex items-center justify-between border-t border-slate-50">
                        <div className="flex flex-col">
                          <span className="text-[9px] uppercase text-slate-400 font-bold tracking-widest">Base do Plano</span>
                          <span className={`text-[10px] font-bold ${planValue ? 'text-emerald-600' : 'text-slate-400'}`}>
                            {planValue ? 'Ativo no Plano' : 'Bloqueado no Plano'}
                          </span>
                        </div>
                        {isEnabled && !planValue && (
                          <Badge className="bg-indigo-50 text-indigo-600 border-none text-[9px] font-black">UPSALE</Badge>
                        )}
                      </div>
                    </div>

                    {/* Pulse indicator for active features */}
                    {isEnabled && (
                      <div className="absolute -top-1 -right-1">
                        <div className="w-4 h-4 bg-indigo-500/10 rounded-full animate-ping" />
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
