'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { getFeatures, updateFeatures } from '@/lib/features';
import { useToast } from '@/hooks/use-toast';
import {
  Calendar, MessageSquare, StickyNote, Paperclip, Zap, Search,
  BarChart3, Archive, Mic, Shield, RefreshCw, Brain, Save, Loader2,
  Lock
} from 'lucide-react';

interface Feature {
  key: string;
  name: string;
  description: string;
  icon: any;
  category: 'core' | 'advanced' | 'experimental';
  comingSoon?: boolean;
  requiresPremium?: boolean;
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
    category: 'advanced',
    requiresPremium: true
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
    category: 'advanced',
    requiresPremium: true
  },

  // Experimental Features
  {
    key: 'ai_guard_enabled',
    name: 'Guardrails Avançados',
    description: 'Proteções de preço, concorrentes, etc',
    icon: Shield,
    category: 'experimental',
    requiresPremium: true
  },
  {
    key: 'reengagement_enabled',
    name: 'Re-engajamento Automático',
    description: 'Follow-ups automáticos para leads inativos',
    icon: RefreshCw,
    category: 'experimental',
    requiresPremium: true
  },
  {
    key: 'knowledge_base_enabled',
    name: 'Base de Conhecimento (RAG)',
    description: 'IA busca respostas em documentos',
    icon: Brain,
    category: 'experimental',
    comingSoon: true,
    requiresPremium: true
  },
];

export default function ControlCenterPage() {
  const [features, setFeatures] = useState<Record<string, boolean>>({});
  const [planFeatures, setPlanFeatures] = useState<Record<string, boolean>>({});
  const [teamFeatures, setTeamFeatures] = useState<Record<string, boolean>>({});
  const [planName, setPlanName] = useState('');
  const [canEdit, setCanEdit] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadFeatures();
  }, []);

  async function loadFeatures() {
    try {
      setLoading(true);
      const data = await getFeatures();

      console.log('🎛️ Features carregadas:', data);

      setFeatures(data.final_features);
      setPlanFeatures(data.plan_features);
      setTeamFeatures(data.team_features);
      setPlanName(data.plan_name);
      setCanEdit(data.can_edit);
    } catch (err) {
      console.error('Erro ao carregar features:', err);
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar configurações',
        description: 'Tente novamente'
      });
    } finally {
      setLoading(false);
    }
  }

  function handleToggle(key: string) {
    // Verificar se a feature está disponível no plano
    if (!planFeatures[key]) {
      toast({
        variant: 'destructive',
        title: 'Feature não disponível',
        description: 'Esta funcionalidade não está incluída no seu plano atual.'
      });
      return;
    }

    // Atualizar estado local
    const newTeamFeatures = { ...teamFeatures, [key]: !teamFeatures[key] };
    setTeamFeatures(newTeamFeatures);
    setFeatures({ ...planFeatures, ...newTeamFeatures });
    setHasChanges(true);
  }

  async function handleSave() {
    try {
      setSaving(true);
      await updateFeatures(teamFeatures);
      setHasChanges(false);
      toast({
        title: 'Configurações salvas!',
        description: 'As funcionalidades foram atualizadas'
      });
    } catch (err: any) {
      console.error('Erro ao salvar:', err);
      toast({
        variant: 'destructive',
        title: 'Erro ao salvar',
        description: err.message || 'Tente novamente'
      });
    } finally {
      setSaving(false);
    }
  }

  const categories = {
    core: FEATURES.filter(f => f.category === 'core'),
    advanced: FEATURES.filter(f => f.category === 'advanced'),
    experimental: FEATURES.filter(f => f.category === 'experimental'),
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!canEdit) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <div className="text-center py-12">
          <Lock className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Acesso Restrito</h2>
          <p className="text-gray-500">Apenas gestores e administradores podem acessar o Centro de Controle.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Centro de Controle</h1>
          <p className="text-gray-500 mt-1">
            Ative ou desative funcionalidades do sistema • Plano: <Badge className="ml-2">{planName}</Badge>
          </p>
        </div>

        {hasChanges && (
          <Button
            onClick={handleSave}
            disabled={saving}
            size="lg"
            className="gap-2"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Salvando...' : 'Salvar Alterações'}
          </Button>
        )}
      </div>

      {/* Core Features */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Badge className="bg-blue-100 text-blue-700">Essenciais</Badge>
          Funcionalidades Principais
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.core.map(feature => (
            <FeatureCard
              key={feature.key}
              feature={feature}
              enabled={teamFeatures[feature.key] ?? planFeatures[feature.key] ?? false}
              availableInPlan={planFeatures[feature.key] ?? false}
              onToggle={() => handleToggle(feature.key)}
              loading={loading}
            />
          ))}
        </div>
      </section>

      {/* Advanced Features */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Badge className="bg-purple-100 text-purple-700">Avançadas</Badge>
          Recursos Premium
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.advanced.map(feature => (
            <FeatureCard
              key={feature.key}
              feature={feature}
              enabled={teamFeatures[feature.key] ?? planFeatures[feature.key] ?? false}
              availableInPlan={planFeatures[feature.key] ?? false}
              onToggle={() => handleToggle(feature.key)}
              loading={loading}
            />
          ))}
        </div>
      </section>

      {/* Experimental Features */}
      <section>
        <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Badge className="bg-orange-100 text-orange-700">Experimental</Badge>
          Em Desenvolvimento
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.experimental.map(feature => (
            <FeatureCard
              key={feature.key}
              feature={feature}
              enabled={teamFeatures[feature.key] ?? planFeatures[feature.key] ?? false}
              availableInPlan={planFeatures[feature.key] ?? false}
              onToggle={() => handleToggle(feature.key)}
              loading={loading}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function FeatureCard({
  feature,
  enabled,
  availableInPlan,
  onToggle,
  loading
}: {
  feature: Feature;
  enabled: boolean;
  availableInPlan: boolean;
  onToggle: () => void;
  loading: boolean;
}) {
  const Icon = feature.icon;
  const isLocked = !availableInPlan;

  return (
    <Card className={`p-4 transition ${enabled && !isLocked ? 'border-blue-500 bg-blue-50/30' : ''} ${isLocked ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${enabled && !isLocked ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-500'}`}>
            <Icon className="w-5 h-5" />
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-800">{feature.name}</h3>
              {feature.comingSoon && (
                <Badge variant="outline" className="text-xs">Em breve</Badge>
              )}
              {isLocked && (
                <Badge variant="outline" className="text-xs flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  Plano Superior
                </Badge>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-1">{feature.description}</p>
          </div>
        </div>

        <Switch
          checked={enabled && availableInPlan}
          onCheckedChange={onToggle}
          disabled={loading || feature.comingSoon || isLocked}
        />
      </div>
    </Card>
  );
}
