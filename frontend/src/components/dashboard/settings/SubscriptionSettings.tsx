'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { getToken } from '@/lib/auth';
import {
    Calendar, MessageSquare, StickyNote, Paperclip, Zap, Search,
    BarChart3, Archive, Mic, Shield, RefreshCw, UserCheck, HeartPulse,
    EyeOff, Lock, Users, Brain, RotateCcw, Save, Loader2, AlertCircle
} from 'lucide-react';

interface SubscriptionSettingsProps {
    targetTenantId: number | null;
    isSuperAdmin: boolean;
    currentTenant: any;
    onPlanChange?: (planId: string) => void;
}

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

export default function SubscriptionSettings({
    targetTenantId,
    isSuperAdmin,
    currentTenant,
    onPlanChange
}: SubscriptionSettingsProps) {
    const [planFeatures, setPlanFeatures] = useState<Record<string, boolean>>({});
    const [overrides, setOverrides] = useState<Record<string, boolean>>({});
    const [finalFeatures, setFinalFeatures] = useState<Record<string, boolean>>({});

    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const { toast } = useToast();

    useEffect(() => {
        loadFeatures();
    }, [targetTenantId]);

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
                    'X-Tenant-Override': targetTenantId ? targetTenantId.toString() : ''
                },
            });

            if (!response.ok) throw new Error('Erro ao carregar features');

            const data = await response.json();

            setPlanFeatures(data.plan_features || {});
            setOverrides(data.overrides || {});
            setFinalFeatures(data.final_features || data);
        } catch (err) {
            console.error('❌ Erro:', err);
            toast({ variant: 'destructive', title: 'Erro de conexão', description: 'Não foi possível carregar as configurações de features.' });
        } finally {
            setLoading(false);
        }
    }

    async function handleToggle(key: string, enabled: boolean) {
        if (!isSuperAdmin) return; // Só superadmin pode alterar features individuais
        const newOverrides = { ...overrides, [key]: enabled };
        setOverrides(newOverrides);
        setFinalFeatures({ ...planFeatures, ...newOverrides });
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
                    'X-Tenant-Override': targetTenantId ? targetTenantId.toString() : ''
                },
                body: JSON.stringify(targetOverrides),
            });

            if (!response.ok) throw new Error('Erro ao salvar');

            toast({ title: 'Configurações Salvas', description: 'Permissões do cliente atualizadas.' });
            loadFeatures();
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Erro ao salvar', description: err.message });
        } finally {
            setSaving(false);
        }
    }

    async function resetToDefaults() {
        await saveOverrides({});
        setOverrides({});
        toast({ title: 'Resetado!', description: 'Voltamos para as configurações padrão do plano.' });
    }

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

            if (onPlanChange) onPlanChange(planId);

            // Feature list update is handled by the parent trigger or reload, 
            // but we should reload here too just in case
            setTimeout(loadFeatures, 500);

        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Falha na atualização', description: err.message });
        } finally {
            setSaving(false);
        }
    }

    const sections = [
        { title: 'Core Business', badge: 'Essenciais', category: 'core', color: 'bg-blue-100 text-blue-700' },
        { title: 'AI & Intelligence', badge: 'Premium', category: 'advanced', color: 'bg-purple-100 text-purple-700' },
        { title: 'Governance & Security', badge: 'Segurança', category: 'security', color: 'bg-emerald-100 text-emerald-700' },
        { title: 'Future Labs', badge: 'Experimental', category: 'experimental', color: 'bg-orange-100 text-orange-700' }
    ];

    if (loading && Object.keys(finalFeatures).length === 0) {
        return <div className="flex justify-center p-8"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>;
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">

            {/* Header de Controle (Só SuperAdmin) */}
            {isSuperAdmin && targetTenantId && (
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-slate-50 p-6 rounded-2xl border border-slate-200">
                    <div className="space-y-1">
                        <h2 className="text-xl font-bold text-slate-900">Plano & Assinatura</h2>
                        <p className="text-sm text-slate-500">Controle o nível de assinatura e recursos disponíveis</p>
                    </div>

                    <div className="flex items-center gap-2">
                        {PLANS.map(p => (
                            <button
                                key={p.id}
                                onClick={() => handlePlanChange(p.id)}
                                disabled={saving}
                                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${currentTenant?.plan === p.id ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-200' : 'text-slate-400 hover:text-slate-600'}`}
                            >
                                {p.name}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Warning if no tenant selected by SuperAdmin */}
            {isSuperAdmin && !targetTenantId && (
                <div className="bg-amber-50 border border-amber-100 p-6 rounded-2xl flex items-center gap-4 text-amber-800">
                    <AlertCircle className="w-6 h-6 flex-shrink-0" />
                    <div>
                        <p className="font-bold">Modo de Visualização (Próprio)</p>
                        <p className="text-sm opacity-80">Você está visualizando os recursos do ADMIN. Para provisionar outros status, selecione um cliente no menu superior.</p>
                    </div>
                </div>
            )}

            <div className="flex justify-end gap-3">
                {isSuperAdmin && targetTenantId && (
                    <>
                        <Button
                            variant="outline"
                            onClick={resetToDefaults}
                            disabled={saving}
                            className="gap-2 text-slate-600"
                        >
                            <RotateCcw className="w-4 h-4" />
                            Resetar Overrides
                        </Button>
                        <Button
                            onClick={() => saveOverrides()}
                            disabled={saving}
                            className="bg-indigo-600 hover:bg-indigo-700 gap-2 font-bold"
                        >
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            Salvar Recusos
                        </Button>
                    </>
                )}
            </div>

            <div className="space-y-12">
                {sections.map(section => (
                    <div key={section.category} className="space-y-6">
                        <div className="flex items-center gap-4 overflow-hidden">
                            <h3 className="text-lg font-bold text-slate-800 whitespace-nowrap">{section.title}</h3>
                            <div className="h-px bg-slate-100 flex-1" />
                            <Badge className={`${section.color} border-none font-bold`}>{section.badge}</Badge>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
                            {FEATURES.filter(f => f.category === section.category).map(f => {
                                const isOverridden = overrides.hasOwnProperty(f.key);
                                const isEnabled = finalFeatures[f.key] ?? false;
                                const planValue = planFeatures[f.key] ?? false;

                                return (
                                    <Card
                                        key={f.key}
                                        className={`relative group p-5 rounded-2xl transition-all duration-300 border overflow-hidden ${isEnabled ? 'border-indigo-200 bg-white shadow-sm' : 'border-slate-100 bg-slate-50/50 opacity-80'}`}
                                    >
                                        <div className="flex flex-col gap-3 h-full">
                                            <div className="flex items-start justify-between">
                                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${isEnabled ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'}`}>
                                                    <f.icon className="w-5 h-5" />
                                                </div>
                                                <div className="flex flex-col items-end gap-1">
                                                    <Switch
                                                        checked={isEnabled}
                                                        onCheckedChange={(val) => handleToggle(f.key, val)}
                                                        disabled={!isSuperAdmin || loading || f.comingSoon || !targetTenantId}
                                                        className="data-[state=checked]:bg-indigo-600 scale-90"
                                                    />
                                                    {isOverridden && (
                                                        <span className="text-[9px] font-black text-indigo-600 uppercase tracking-tighter">Override</span>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="space-y-1">
                                                <h4 className="font-bold text-slate-900 leading-tight flex items-center gap-2 text-sm">
                                                    {f.name}
                                                    {f.comingSoon && <span className="text-[9px] bg-slate-200 px-1 rounded uppercase">Breve</span>}
                                                </h4>
                                                <p className="text-xs text-slate-500 font-medium leading-normal line-clamp-2">{f.description}</p>
                                            </div>

                                            <div className="mt-auto pt-3 flex items-center justify-between border-t border-slate-50">
                                                {/* Plan Status Indicator */}
                                                <div className="flex items-center gap-1.5">
                                                    <div className={`w-1.5 h-1.5 rounded-full ${planValue ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                                                    <span className="text-[10px] text-slate-400 font-medium">Plano</span>
                                                </div>

                                                {isEnabled && !planValue && (
                                                    <Badge className="bg-indigo-50 text-indigo-600 border-none text-[9px] font-black px-1.5 py-0">UPSALE</Badge>
                                                )}
                                            </div>
                                        </div>
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
