'use client';

import { useState, useEffect, Suspense } from 'react';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { getToken, getUser } from '@/lib/auth';
import { useSearchParams } from 'next/navigation';
import {
  Calendar, MessageSquare, StickyNote, Paperclip, Zap, Search,
  BarChart3, Archive, Mic, Shield, RefreshCw, Brain, Save, Loader2,
  UserCheck, HeartPulse, EyeOff, Lock, Users, Bell, ChevronDown, CheckCircle2,
  Bot, Rocket, Sparkles, CreditCard
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
  {
    key: 'calendar_enabled',
    name: 'Calendário de Agendamentos',
    description: 'Permite vendedores agendarem visitas com leads',
    icon: Calendar,
    category: 'core'
  },
  {
    key: 'templates_enabled',
    name: 'Templates de Resposta',
    description: 'Mensagens pré-definidas com variáveis dinâmicas',
    icon: MessageSquare,
    category: 'core'
  },
  {
    key: 'notes_enabled',
    name: 'Anotações Internas',
    description: 'Notas privadas da equipe sobre leads',
    icon: StickyNote,
    category: 'core'
  },
  {
    key: 'attachments_enabled',
    name: 'Upload de Anexos',
    description: 'Envio de imagens, PDFs e documentos',
    icon: Paperclip,
    category: 'core'
  },

  // Advanced Features
  {
    key: 'sse_enabled',
    name: 'Atualizações em Tempo Real',
    description: 'Mensagens aparecem instantaneamente (SSE)',
    icon: Zap,
    category: 'advanced'
  },
  {
    key: 'search_enabled',
    name: 'Busca de Mensagens',
    description: 'Full-text search em todo histórico',
    icon: Search,
    category: 'advanced'
  },
  {
    key: 'metrics_enabled',
    name: 'Métricas e Analytics',
    description: 'Dashboards com KPIs e performance',
    icon: BarChart3,
    category: 'advanced'
  },
  {
    key: 'archive_enabled',
    name: 'Arquivamento de Leads',
    description: 'Organização de leads inativos',
    icon: Archive,
    category: 'advanced'
  },
  {
    key: 'voice_response_enabled',
    name: 'Respostas em Áudio',
    description: 'IA responde com mensagens de voz',
    icon: Mic,
    category: 'advanced'
  },
  {
    key: 'ai_auto_handoff_enabled',
    name: 'Auto-Transferência (IA)',
    description: 'Transfere para o vendedor assim que qualificado',
    icon: UserCheck,
    category: 'advanced'
  },
  {
    key: 'ai_sentiment_alerts_enabled',
    name: 'Alertas de Sentimento',
    description: 'Monitora humor e urgência dos leads (IA)',
    icon: HeartPulse,
    category: 'advanced'
  },

  // Security Features
  {
    key: 'security_ghost_mode_enabled',
    name: 'Modo Privacidade',
    description: 'Oculta telefone dos leads para os vendedores',
    icon: EyeOff,
    category: 'security'
  },
  {
    key: 'security_export_lock_enabled',
    name: 'Trava de Exportação',
    description: 'Apenas Admins Master podem baixar dados',
    icon: Lock,
    category: 'security'
  },
  {
    key: 'distrib_auto_assign_enabled',
    name: 'Atribuição Inteligente',
    description: 'Distribuição automática ativada globalmente',
    icon: Users,
    category: 'security'
  },

  // Experimental Features
  {
    key: 'ai_guard_enabled',
    name: 'Guardrails Avançados',
    description: 'Proteções de preço, concorrentes, etc',
    icon: Shield,
    category: 'experimental'
  },
  {
    key: 'reengagement_enabled',
    name: 'Re-engajamento Automático',
    description: 'Follow-ups automáticos para leads inativos',
    icon: RefreshCw,
    category: 'experimental'
  },
  {
    key: 'knowledge_base_enabled',
    name: 'Base de Conhecimento (RAG)',
    description: 'IA busca respostas em documentos',
    icon: Brain,
    category: 'experimental',
    comingSoon: true
  },
];

const PLANS = [
  { id: 'starter', name: 'Starter (Básico)', color: 'bg-blue-100 text-blue-700' },
  { id: 'premium', name: 'Premium (Avançado)', color: 'bg-purple-100 text-purple-700' },
  { id: 'enterprise', name: 'Enterprise (Completo)', color: 'bg-indigo-100 text-indigo-700' }
];

export default function ControlCenterPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>}>
      <ControlCenterContent />
    </Suspense>
  );
}

function ControlCenterContent() {
  const [features, setFeatures] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [availableTenants, setAvailableTenants] = useState<any[]>([]);
  const [currentTenantName, setCurrentTenantName] = useState('');
  const [currentPlan, setCurrentPlan] = useState('starter');

  const searchParams = useSearchParams();
  const { toast } = useToast();

  const targetTenantId = searchParams.get('target_tenant_id');

  useEffect(() => {
    const user = getUser();
    const isSuper = !!user?.is_superadmin || user?.role === 'superadmin';
    setIsSuperAdmin(isSuper);

    if (isSuper) {
      fetchTenants();
    }
  }, []);

  useEffect(() => {
    loadFeatures();
  }, [targetTenantId]);

  useEffect(() => {
    if (targetTenantId && availableTenants.length > 0) {
      const tenant = availableTenants.find(t => t.id === parseInt(targetTenantId));
      if (tenant) {
        setCurrentTenantName(tenant.name);
        setCurrentPlan(tenant.plan || 'starter');
      }
    }
  }, [targetTenantId, availableTenants]);

  async function fetchTenants() {
    try {
      const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://vellarys-production.up.railway.app/api/v1').replace(/\/v1$/, '/api/v1');
      const token = getToken();
      const response = await fetch(`${apiUrl}/admin/tenants`, {
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

  const handleTenantChange = (id: number) => {
    const url = new URL(window.location.href);
    url.searchParams.set('target_tenant_id', id.toString());
    window.location.href = url.pathname + url.search;
  };

  async function handlePlanChange(planId: string) {
    if (!targetTenantId) return;

    try {
      setSaving(true);
      const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://vellarys-production.up.railway.app/api/v1').replace(/\/v1$/, '/api/v1');
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

      setCurrentPlan(planId);
      toast({ title: 'Plano Atualizado!', description: `O cliente agora é ${planId.toUpperCase()}.` });

      // Recarrega as features para ver o que mudou automaticamente
      setTimeout(() => loadFeatures(), 1000);

    } catch (err: any) {
      toast({ variant: 'destructive', title: 'Erro ao mudar plano', description: err.message });
    } finally {
      setSaving(false);
    }
  }

  async function loadFeatures() {
    try {
      setLoading(true);
      const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://vellarys-production.up.railway.app/api/v1').replace(/\/v1$/, '/api/v1');
      const token = getToken();

      let url = `${apiUrl}/settings/features`;
      if (targetTenantId) {
        url += `?target_tenant_id=${targetTenantId}`;
      }

      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Erro ao carregar features');

      const data = await response.json();
      setFeatures(data.features || data);
    } catch (err) {
      console.error('❌ Erro:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleToggle(key: string) {
    setFeatures(prev => ({ ...prev, [key]: !prev[key] }));
    setHasChanges(true);
  }

  async function handleSave() {
    try {
      setSaving(true);
      const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://vellarys-production.up.railway.app/api/v1').replace(/\/v1$/, '/api/v1');
      const token = getToken();

      let url = `${apiUrl}/settings/features`;
      if (targetTenantId) {
        url += `?target_tenant_id=${targetTenantId}`;
      }

      const response = await fetch(url, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(features),
      });

      if (!response.ok) throw new Error('Erro ao salvar');

      setHasChanges(false);
      toast({
        title: 'Provisionamento Concluído!',
        description: 'As funcionalidades do cliente foram atualizadas.'
      });
    } catch (err: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao salvar',
        description: err.message
      });
    } finally {
      setSaving(false);
    }
  }

  const categories = {
    core: FEATURES.filter(f => f.category === 'core'),
    advanced: FEATURES.filter(f => f.category === 'advanced'),
    security: FEATURES.filter(f => f.category === 'security'),
    experimental: FEATURES.filter(f => f.category === 'experimental'),
  };

  const planInfo = PLANS.find(p => p.id === currentPlan) || PLANS[0];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* SuperAdmin Tenant Selector */}
      {isSuperAdmin && (
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between group">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Gestão de Clientes</p>
              <h3 className="font-semibold text-gray-900">
                {targetTenantId ? (currentTenantName || `Cliente ID: ${targetTenantId}`) : 'Meu Próprio Plano'}
              </h3>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2">
                Trocar Cliente
                <ChevronDown className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              <DropdownMenuLabel>Selecione um Cliente</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <div className="max-h-60 overflow-y-auto">
                <DropdownMenuItem onClick={() => {
                  const url = new URL(window.location.href);
                  url.searchParams.delete('target_tenant_id');
                  window.location.href = url.pathname + url.search;
                }}>
                  Meu Próprio Plano
                </DropdownMenuItem>
                {availableTenants.map((tenant) => (
                  <DropdownMenuItem key={tenant.id} onClick={() => handleTenantChange(tenant.id)}>
                    <div className="flex items-center justify-between w-full">
                      {tenant.name}
                      {targetTenantId === tenant.id.toString() && <CheckCircle2 className="w-4 h-4 text-blue-600" />}
                    </div>
                  </DropdownMenuItem>
                ))}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}

      {/* Plan Status & Switcher */}
      {targetTenantId && (
        <Card className="p-5 border-indigo-100 bg-indigo-50/10 shadow-lg shadow-indigo-100/20">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-200">
                <CreditCard className="w-6 h-6 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Nível de Acesso</span>
                  <Badge className={`${planInfo.color} border-none`}>{planInfo.name}</Badge>
                </div>
                <h2 className="text-xl font-bold text-gray-900">Configuração de Plano Automática</h2>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-white p-1 rounded-xl border border-indigo-100">
              {PLANS.map((plan) => (
                <button
                  key={plan.id}
                  onClick={() => handlePlanChange(plan.id)}
                  className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${currentPlan === plan.id ? 'bg-indigo-600 text-white shadow-md' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'}`}
                >
                  {plan.name.split(' ')[0]}
                </button>
              ))}
            </div>
          </div>
        </Card>
      )}

      <div className="flex items-center justify-between pt-4 border-t">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            Centro de Controle
            <Sparkles className="w-6 h-6 text-yellow-500 fill-yellow-500" />
          </h1>
          <p className="text-gray-500 mt-1">
            {targetTenantId ? `Personalizando permissões para ${currentTenantName}` : 'Gerencie as funcionalidades da sua conta'}
          </p>
        </div>

        {hasChanges && (
          <Button onClick={handleSave} disabled={saving} size="lg" className="gap-2 shadow-xl shadow-blue-100 animate-bounce">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Salvar Exceção Manual
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-8">
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-blue-100 text-blue-700">MÓDULOS ESSENCIAIS</Badge>
            {currentPlan === 'starter' && <span className="text-xs text-blue-600 font-medium italic">Incluídos no seu plano</span>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.core.map(f => (
              <FeatureCard key={f.key} feature={f} enabled={features[f.key] ?? false} onToggle={() => handleToggle(f.key)} loading={loading} />
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-purple-100 text-purple-700">INTELIGÊNCIA ARTIFICIAL</Badge>
            {currentPlan === 'starter' && <span className="text-xs text-red-500 font-medium animate-pulse flex items-center gap-1"><Lock className="w-3 h-3" /> Requer Plano Premium</span>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.advanced.map(f => (
              <FeatureCard key={f.key} feature={f} enabled={features[f.key] ?? false} onToggle={() => handleToggle(f.key)} loading={loading} disabled={currentPlan === 'starter' && !features[f.key]} />
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-emerald-100 text-emerald-700">SEGURANÇA & DADOS</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.security.map(f => (
              <FeatureCard key={f.key} feature={f} enabled={features[f.key] ?? false} onToggle={() => handleToggle(f.key)} loading={loading} />
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-orange-100 text-orange-700">LABORATÓRIO BETA</Badge>
            {currentPlan !== 'enterprise' && <span className="text-xs text-orange-600 font-medium flex items-center gap-1"><Lock className="w-3 h-3" /> Requer Plano Enterprise</span>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.experimental.map(f => (
              <FeatureCard key={f.key} feature={f} enabled={features[f.key] ?? false} onToggle={() => handleToggle(f.key)} loading={loading} disabled={currentPlan !== 'enterprise' && !features[f.key]} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function FeatureCard({ feature, enabled, onToggle, loading, disabled }: { feature: Feature, enabled: boolean, onToggle: () => void, loading: boolean, disabled?: boolean }) {
  const Icon = feature.icon;
  return (
    <Card className={`relative overflow-hidden p-5 transition-all duration-300 border-2 ${enabled ? 'border-blue-500 bg-blue-50/20 shadow-md' : 'border-gray-100 hover:border-gray-200 shadow-sm'} ${disabled ? 'opacity-50 grayscale' : ''}`}>
      <div className="flex items-start justify-between">
        <div className="flex gap-4">
          <div className={`p-3 rounded-2xl transition-colors ${enabled ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'}`}>
            <Icon className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-gray-900 leading-none">{feature.name}</h3>
              {feature.comingSoon && <Badge variant="outline" className="text-[10px] h-4">SOON</Badge>}
            </div>
            <p className="text-xs text-gray-500 leading-relaxed font-medium">{feature.description}</p>
          </div>
        </div>
        <Switch checked={enabled} onCheckedChange={onToggle} disabled={loading || feature.comingSoon || disabled} className="data-[state=checked]:bg-blue-600" />
      </div>
      {enabled && <div className="absolute top-0 right-0 p-1"><div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" /></div>}
      {disabled && <Lock className="absolute top-2 right-2 w-4 h-4 text-gray-400" />}
    </Card>
  );
}
