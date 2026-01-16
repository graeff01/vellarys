'use client';

// Adicionar esses imports
import ProductsTab from '@/components/dashboard/ProductsTab';
import { getSellers } from '@/lib/sellers';
import { getToken } from '@/lib/auth';
import { useEffect, useState, useCallback } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { requestNotificationPermission, subscribeToPush } from '@/components/pwa/service-worker-registration';
import {
  getSettings, updateSettings,
  SettingsResponse, TenantSettings,
  ToneOption, PersonalityTrait,
  DistributionMethod, FallbackOption, NicheOption,
  RequiredInfoOption, FAQItem,
  DEFAULT_IDENTITY,

} from '@/lib/settings';
import {
  Save, X, Phone,
  Shield, CheckCircle2, ChevronDown,
  Trash2, Package, Library, Sparkles
} from 'lucide-react';

// Adicionar esses imports
import {
  checkProductsAccess,
  getProducts,
  getProduct,
  createProduct,
  updateProduct,
  deleteProduct,
  toggleProductStatus,
  Product,
  ProductCreate,
} from '@/lib/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
}

function TagInput({ tags, onChange, placeholder = "Digite e pressione Enter", maxTags = 20 }: TagInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault();
      if (tags.length < maxTags && !tags.includes(inputValue.trim())) {
        onChange([...tags, inputValue.trim()]);
        setInputValue('');
      }
    }
  };

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <span key={i} className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm">
            {tag}
            <button onClick={() => removeTag(i)} className="hover:bg-blue-200 rounded-full p-0.5">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
}

function ToggleSwitch({ checked, onChange, label, description }: ToggleSwitchProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="font-medium text-gray-900">{label}</p>
        {description && <p className="text-sm text-gray-500">{description}</p>}
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="sr-only peer" />
        <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
      </label>
    </div>
  );
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================


export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState('perfil');


  // IDENTIDADE
  const [companyName, setCompanyName] = useState('');
  const [niche, setNiche] = useState('services');
  const [description, setDescription] = useState('');
  const [productsServices, setProductsServices] = useState<string[]>([]);
  const [notOffered, setNotOffered] = useState<string[]>([]);
  const [tone, setTone] = useState<'formal' | 'cordial' | 'informal' | 'tecnico'>('cordial');
  const [personalityTraits, setPersonalityTraits] = useState<string[]>([]);
  const [communicationStyle, setCommunicationStyle] = useState('');
  const [avoidPhrases, setAvoidPhrases] = useState<string[]>([]);
  const [usePhrases, setUsePhrases] = useState<string[]>([]);
  const [targetAudienceDesc, setTargetAudienceDesc] = useState('');
  const [targetSegments, setTargetSegments] = useState<string[]>([]);
  const [painPoints, setPainPoints] = useState<string[]>([]);
  const [businessRules, setBusinessRules] = useState<string[]>([]);
  const [differentials, setDifferentials] = useState<string[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [requiredQuestions, setRequiredQuestions] = useState<string[]>([]);
  const [requiredInfo, setRequiredInfo] = useState<string[]>([]);
  const [additionalContext, setAdditionalContext] = useState('');

  // HANDOFF
  const [managerWhatsapp, setManagerWhatsapp] = useState('');
  const [managerName, setManagerName] = useState('');
  const [handoffEnabled, setHandoffEnabled] = useState(true);
  const [handoffTriggers, setHandoffTriggers] = useState<string[]>([]);
  const [maxMessages, setMaxMessages] = useState(15);

  // HORÁRIO
  const [businessHoursEnabled, setBusinessHoursEnabled] = useState(false);
  const [businessHours, setBusinessHours] = useState<Record<string, { open: string, close: string, enabled: boolean }>>({
    monday: { open: '08:00', close: '18:00', enabled: true },
    tuesday: { open: '08:00', close: '18:00', enabled: true },
    wednesday: { open: '08:00', close: '18:00', enabled: true },
    thursday: { open: '08:00', close: '18:00', enabled: true },
    friday: { open: '08:00', close: '18:00', enabled: true },
    saturday: { open: '08:00', close: '12:00', enabled: false },
    sunday: { open: '', close: '', enabled: false },
  });
  const [outOfHoursMessage, setOutOfHoursMessage] = useState('');

  // FAQ
  const [faqEnabled, setFaqEnabled] = useState(true);
  const [faqItems, setFaqItems] = useState<FAQItem[]>([]);
  const [newFaqQuestion, setNewFaqQuestion] = useState('');
  const [newFaqAnswer, setNewFaqAnswer] = useState('');

  // ESCOPO
  const [scopeEnabled, setScopeEnabled] = useState(true);
  const [scopeDescription, setScopeDescription] = useState('');
  const [allowedTopics, setAllowedTopics] = useState<string[]>([]);
  const [blockedTopics, setBlockedTopics] = useState<string[]>([]);
  const [outOfScopeMessage, setOutOfScopeMessage] = useState('');

  // DISTRIBUIÇÃO
  const [distributionMethod, setDistributionMethod] = useState('round_robin');
  const [distributionFallback, setDistributionFallback] = useState('manager');
  const [respectDailyLimit, setRespectDailyLimit] = useState(true);
  const [respectAvailability, setRespectAvailability] = useState(true);
  const [notifyManagerCopy, setNotifyManagerCopy] = useState(false);
  const [notifyBrokerRaiox, setNotifyBrokerRaiox] = useState(true);
  const [minMessagesBrokerRaiox, setMinMessagesBrokerRaiox] = useState(3);

  // GUARDRAILS
  const [priceGuardEnabled, setPriceGuardEnabled] = useState(true);
  const [priceGuardBehavior, setPriceGuardBehavior] = useState<'redirect' | 'collect_first' | 'allow'>('redirect');
  const [priceGuardMessage, setPriceGuardMessage] = useState('');
  const [scopeGuardEnabled, setScopeGuardEnabled] = useState(true);
  const [scopeGuardStrictness, setScopeGuardStrictness] = useState<'low' | 'medium' | 'high'>('medium');

  // FOLLOW-UP
  const [followUpEnabled, setFollowUpEnabled] = useState(false);
  const [followUpInactivityHours, setFollowUpInactivityHours] = useState(24);
  const [followUpMaxAttempts, setFollowUpMaxAttempts] = useState(3);
  const [followUpIntervalHours, setFollowUpIntervalHours] = useState(24);
  const [followUpRespectBusinessHours, setFollowUpRespectBusinessHours] = useState(true);
  const [followUpMessages, setFollowUpMessages] = useState({
    attempt_1: "Oi {nome}! Vi que você se interessou por {interesse}. Posso te ajudar com mais alguma informação? 😊",
    attempt_2: "Oi {nome}! Ainda está procurando {interesse}? Estou aqui se precisar!",
    attempt_3: "{nome}, vou encerrar nosso atendimento por aqui. Se precisar, é só chamar novamente! 👋",
  });
  const [followUpExcludeStatuses, setFollowUpExcludeStatuses] = useState<string[]>(['converted', 'lost', 'handed_off']);

  // Após os outros estados, adicionar:
  const [hasProductsAccess, setHasProductsAccess] = useState(false);
  const [sellers, setSellers] = useState<Array<{ id: number; name: string }>>([]);


  // OPTIONS
  // ⭐ CORRIGIDO: Inicializa vazio - nichos serão carregados do banco de dados
  const [niches, setNiches] = useState<NicheOption[]>([]);

  const [toneOptions, setToneOptions] = useState<ToneOption[]>([
    { id: 'formal', name: 'Formal', description: 'Profissional, direto e corporativo', icon: '👔', examples: ['Prezado(a)', 'Agradeço o contato', 'Fico à disposição'] },
    { id: 'cordial', name: 'Cordial', description: 'Amigável, educado e acolhedor', icon: '😊', examples: ['Olá!', 'Fico feliz em ajudar', 'Conte comigo'] },
    { id: 'informal', name: 'Informal', description: 'Descontraído, próximo e casual', icon: '🤙', examples: ['Oi!', 'Show!', 'Bora lá'] },
    { id: 'tecnico', name: 'Técnico', description: 'Preciso, detalhado e especializado', icon: '🔬', examples: ['Tecnicamente', 'De acordo com', 'Especificamente'] },
  ]);
  const [personalityOptions, setPersonalityOptions] = useState<PersonalityTrait[]>([
    { id: 'acolhedor', name: 'Acolhedor', description: 'Faz o cliente se sentir bem-vindo' },
    { id: 'objetivo', name: 'Objetivo', description: 'Vai direto ao ponto' },
    { id: 'consultivo', name: 'Consultivo', description: 'Orienta e aconselha' },
    { id: 'entusiasmado', name: 'Entusiasmado', description: 'Demonstra empolgação' },
    { id: 'paciente', name: 'Paciente', description: 'Explica com calma' },
    { id: 'profissional', name: 'Profissional', description: 'Mantém formalidade' },
    { id: 'empatico', name: 'Empático', description: 'Demonstra compreensão' },
    { id: 'proativo', name: 'Proativo', description: 'Antecipa necessidades' },
  ]);
  const [distributionMethods, setDistributionMethods] = useState<DistributionMethod[]>([
    { id: 'round_robin', name: 'Rodízio', description: 'Distribui igualmente entre todos', icon: '🔄' },
    { id: 'by_city', name: 'Por Cidade', description: 'Vendedor que atende a cidade', icon: '📍' },
    { id: 'by_specialty', name: 'Por Especialidade', description: 'Vendedor com a especialidade', icon: '🎯' },
    { id: 'least_busy', name: 'Menos Ocupado', description: 'Vendedor com menos leads no dia', icon: '⚖️' },
    { id: 'manual', name: 'Manual', description: 'Gestor decide manualmente', icon: '✋' },
  ]);
  const [fallbackOptions, setFallbackOptions] = useState<FallbackOption[]>([
    { id: 'manager', name: 'Enviar para Gestor', description: 'Gestor decide o destino' },
    { id: 'round_robin', name: 'Rodízio Geral', description: 'Distribui entre todos' },
    { id: 'queue', name: 'Fila de Espera', description: 'Aguarda vendedor disponível' },
  ]);
  const [requiredInfoOptions, setRequiredInfoOptions] = useState<RequiredInfoOption[]>([
    { id: 'nome', name: 'Nome', description: 'Nome do cliente' },
    { id: 'telefone', name: 'Telefone', description: 'Telefone de contato' },
    { id: 'email', name: 'E-mail', description: 'E-mail do cliente' },
    { id: 'cidade', name: 'Cidade', description: 'Cidade do cliente' },
    { id: 'bairro', name: 'Bairro', description: 'Bairro do cliente' },
    { id: 'data_preferencia', name: 'Data', description: 'Data preferida' },
    { id: 'horario_preferencia', name: 'Horário', description: 'Horário preferido' },
    { id: 'orcamento', name: 'Orçamento', description: 'Faixa de orçamento' },
    { id: 'como_conheceu', name: 'Como Conheceu', description: 'Origem do lead' },
  ]);

  const dayNames: Record<string, string> = {
    monday: 'Segunda-feira', tuesday: 'Terça-feira', wednesday: 'Quarta-feira',
    thursday: 'Quinta-feira', friday: 'Sexta-feira', saturday: 'Sábado', sunday: 'Domingo',
  };

  // ⭐ CORRIGIDO: Busca nichos do endpoint /tenants/niches (acessível a qualquer usuário)
  async function fetchNiches() {
    try {
      const token = getToken();
      // ⭐ MUDANÇA PRINCIPAL: Usa /tenants/niches ao invés de /admin/niches
      const response = await fetch(`${API_URL}/tenants/niches`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        // O endpoint /tenants/niches já retorna no formato correto: [{id, name, description}, ...]
        const formattedNiches = data.map((n: { id: string; name: string; description?: string }) => ({
          id: n.id,
          name: n.name,
          description: n.description || '',
          icon: '📦',  // Ícone padrão
        }));
        setNiches(formattedNiches);
      }
    } catch (error) {
      console.error('Erro ao carregar nichos:', error);
    }
  }

  // LOAD
  useEffect(() => {
    async function loadSettings() {
      try {
        // ⭐ Busca nichos do banco primeiro
        await fetchNiches();

        const response = await getSettings();
        setData(response);
        const s = response.settings;

        try {
          const accessResponse = await checkProductsAccess();
          setHasProductsAccess(accessResponse.has_access);

          // Se tem acesso, busca os vendedores
          if (accessResponse.has_access) {
            try {
              const sellersResponse = await getSellers(true, false); // activeOnly=true, availableOnly=false
              setSellers(sellersResponse.sellers || []);
            } catch {
              console.error('Erro ao carregar vendedores');
            }
          }
        } catch {
          setHasProductsAccess(false);
        }

        // Basic
        setCompanyName(s.basic?.company_name || response.tenant.name);
        setNiche(s.basic?.niche || 'services');

        // Identity
        const identity = s.identity || DEFAULT_IDENTITY;
        setDescription(identity.description || '');
        setProductsServices(identity.products_services || []);
        setNotOffered(identity.not_offered || []);
        setTone(identity.tone_style?.tone || 'cordial');
        setPersonalityTraits(identity.tone_style?.personality_traits || []);
        setCommunicationStyle(identity.tone_style?.communication_style || '');
        setAvoidPhrases(identity.tone_style?.avoid_phrases || []);
        setUsePhrases(identity.tone_style?.use_phrases || []);
        setTargetAudienceDesc(identity.target_audience?.description || '');
        setTargetSegments(identity.target_audience?.segments || []);
        setPainPoints(identity.target_audience?.pain_points || []);
        setBusinessRules(identity.business_rules || []);
        setDifferentials(identity.differentials || []);
        setKeywords(identity.keywords || []);
        setRequiredQuestions(identity.required_questions || []);
        setRequiredInfo(identity.required_info || []);
        setAdditionalContext(identity.additional_context || '');

        // Handoff
        const handoff = s.handoff || {};
        setHandoffEnabled(handoff.enabled ?? true);
        setManagerWhatsapp(handoff.manager_whatsapp || '');
        setManagerName(handoff.manager_name || '');
        setHandoffTriggers(handoff.triggers || []);
        setMaxMessages(handoff.max_messages_before_handoff || 15);

        // Business Hours
        const bh = s.business_hours || {};
        setBusinessHoursEnabled(bh.enabled || false);
        if (bh.schedule) setBusinessHours(bh.schedule);
        setOutOfHoursMessage(bh.out_of_hours_message || '');

        // FAQ
        const faq = s.faq || {};
        setFaqEnabled(faq.enabled ?? true);
        setFaqItems(faq.items || []);

        // Scope
        const scope = s.scope || {};
        setScopeEnabled(scope.enabled ?? true);
        setScopeDescription(scope.description || '');
        setAllowedTopics(scope.allowed_topics || []);
        setBlockedTopics(scope.blocked_topics || []);
        setOutOfScopeMessage(scope.out_of_scope_message || '');

        // Distribution
        const dist = s.distribution || {};
        setDistributionMethod(dist.method || 'round_robin');
        setDistributionFallback(dist.fallback || 'manager');
        setRespectDailyLimit(dist.respect_daily_limit ?? true);
        setRespectAvailability(dist.respect_availability ?? true);
        setNotifyManagerCopy(dist.notify_manager_copy ?? false);
        setNotifyBrokerRaiox(dist.notify_broker_raiox ?? true);
        setMinMessagesBrokerRaiox(dist.min_messages_broker_raiox ?? 3);

        // Guardrails
        const guards = s.guardrails || {};
        setPriceGuardEnabled(guards.price_guard?.enabled ?? true);
        setPriceGuardBehavior(guards.price_guard?.behavior || 'redirect');
        setPriceGuardMessage(guards.price_guard?.message || '');
        setScopeGuardEnabled(guards.scope_guard?.enabled ?? true);
        setScopeGuardStrictness(guards.scope_guard?.strictness || 'medium');

        // Follow-up
        const followUp = s.follow_up || {};
        setFollowUpEnabled(followUp.enabled ?? false);
        setFollowUpInactivityHours(followUp.inactivity_hours ?? 24);
        setFollowUpMaxAttempts(followUp.max_attempts ?? 3);
        setFollowUpIntervalHours(followUp.interval_hours ?? 24);
        setFollowUpRespectBusinessHours(followUp.respect_business_hours ?? true);
        if (followUp.messages) setFollowUpMessages(followUp.messages);
        if (followUp.exclude_statuses) setFollowUpExcludeStatuses(followUp.exclude_statuses);

        // Options - sobrescreve com dados da API se existirem
        const opts = response.options || {};
        // ⭐ REMOVIDO: Nichos agora vêm do endpoint /tenants/niches
        if (opts.tones && opts.tones.length > 0) setToneOptions(opts.tones);
        if (opts.personality_traits && opts.personality_traits.length > 0) setPersonalityOptions(opts.personality_traits);
        if (opts.distribution_methods && opts.distribution_methods.length > 0) setDistributionMethods(opts.distribution_methods);
        if (opts.fallback_options && opts.fallback_options.length > 0) setFallbackOptions(opts.fallback_options);
        if (opts.required_info_options && opts.required_info_options.length > 0) setRequiredInfoOptions(opts.required_info_options);
      } catch (error) {
        console.error('Erro ao carregar:', error);
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  // SAVE
  const handleSave = async () => {
    setSaving(true);
    setSuccess(false);
    try {
      await updateSettings({
        tenant_name: companyName,
        basic: { niche, company_name: companyName },
        identity: {
          description, products_services: productsServices, not_offered: notOffered,
          tone_style: { tone, personality_traits: personalityTraits, communication_style: communicationStyle, avoid_phrases: avoidPhrases, use_phrases: usePhrases },
          target_audience: { description: targetAudienceDesc, segments: targetSegments, pain_points: painPoints },
          business_rules: businessRules, differentials, keywords, required_questions: requiredQuestions, required_info: requiredInfo, additional_context: additionalContext,
        },
        handoff: { enabled: handoffEnabled, manager_whatsapp: managerWhatsapp, manager_name: managerName, triggers: handoffTriggers, max_messages_before_handoff: maxMessages, transfer_message: '' },
        business_hours: { enabled: businessHoursEnabled, timezone: 'America/Sao_Paulo', schedule: businessHours, out_of_hours_message: outOfHoursMessage, out_of_hours_behavior: 'message_only' },
        faq: { enabled: faqEnabled, items: faqItems },
        scope: { enabled: scopeEnabled, description: scopeDescription, allowed_topics: allowedTopics, blocked_topics: blockedTopics, out_of_scope_message: outOfScopeMessage },
        distribution: {
          method: distributionMethod,
          fallback: distributionFallback,
          respect_daily_limit: respectDailyLimit,
          respect_availability: respectAvailability,
          notify_manager_copy: notifyManagerCopy,
          notify_broker_raiox: notifyBrokerRaiox,
          min_messages_broker_raiox: minMessagesBrokerRaiox,
          last_seller_index: 0
        },
        guardrails: {
          price_guard: { enabled: priceGuardEnabled, behavior: priceGuardBehavior, message: priceGuardMessage },
          competitor_guard: { enabled: false, competitors: [], behavior: 'neutral' },
          scope_guard: { enabled: scopeGuardEnabled, strictness: scopeGuardStrictness },
          insist_guard: { enabled: true, max_attempts: 3, escalate_after: true },
        },
        follow_up: {
          enabled: followUpEnabled,
          inactivity_hours: followUpInactivityHours,
          max_attempts: followUpMaxAttempts,
          interval_hours: followUpIntervalHours,
          respect_business_hours: followUpRespectBusinessHours,
          messages: followUpMessages,
          exclude_statuses: followUpExcludeStatuses,
          exclude_qualifications: [],
          allowed_hours: { start: "08:00", end: "20:00" },
        },
        ai_behavior: { custom_questions: [], custom_rules: [], greeting_message: '', farewell_message: '' },
        messages: { greeting: '', farewell: '', out_of_hours: outOfHoursMessage, out_of_scope: outOfScopeMessage, handoff_notice: '', qualification_complete: '', waiting_response: '' },
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (error) {
      console.error('Erro ao salvar:', error);
      alert('Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  };

  // HELPERS
  const addFaq = () => {
    if (newFaqQuestion.trim() && newFaqAnswer.trim()) {
      setFaqItems([...faqItems, { question: newFaqQuestion.trim(), answer: newFaqAnswer.trim() }]);
      setNewFaqQuestion(''); setNewFaqAnswer('');
    }
  };
  const removeFaq = (i: number) => setFaqItems(faqItems.filter((_, idx) => idx !== i));
  const updateBusinessHour = (day: string, field: 'open' | 'close' | 'enabled', value: string | boolean) => {
    setBusinessHours({ ...businessHours, [day]: { ...businessHours[day], [field]: value } });
  };
  const togglePersonalityTrait = (trait: string) => {
    if (personalityTraits.includes(trait)) setPersonalityTraits(personalityTraits.filter(t => t !== trait));
    else if (personalityTraits.length < 4) setPersonalityTraits([...personalityTraits, trait]);
  };
  const toggleRequiredInfo = (info: string) => {
    if (requiredInfo.includes(info)) setRequiredInfo(requiredInfo.filter(i => i !== info));
    else setRequiredInfo([...requiredInfo, info]);
  };

  if (loading) return <div className="flex items-center justify-center min-h-[400px]"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div></div>;

  const tabs = [
    { id: 'perfil', label: 'Perfil da IA', icon: Sparkles },
    { id: 'atendimento', label: 'Fluxo Comercial', icon: Phone },
    { id: 'conhecimento', label: 'Conhecimento', icon: Library },
    { id: 'avancado', label: 'Avançado', icon: Shield },
  ];

  async function handleEnableNotifications() {
    const granted = await requestNotificationPermission();

    if (!granted) {
      alert('Permissão de notificações negada');
      return;
    }

    const subscription = await subscribeToPush();
    console.log('PUSH SUBSCRIPTION:', subscription);

    alert('Notificações ativadas com sucesso!');
  }


  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Configurações da IA</h1>
          <p className="text-gray-500">
            Configure a identidade e comportamento da sua IA atendente
          </p>

          <button
            onClick={handleEnableNotifications}
            className="mt-3 inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
          >
            🔔 Ativar notificações
          </button>
        </div>


        {activeTab !== 'products' && (
          <button onClick={handleSave} disabled={saving} className="flex items-center justify-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {saving ? <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>Salvando...</> : <><Save className="w-5 h-5" />Salvar</>}
          </button>
        )}
      </div>

      {success && <div className="flex items-center gap-3 bg-green-50 border border-green-200 text-green-700 p-4 rounded-lg"><CheckCircle2 className="w-5 h-5" />Configurações salvas!</div>}

      {/* Tabs */}
      <div className="border-b">
        <div className="sm:hidden">
          <select value={activeTab} onChange={(e) => setActiveTab(e.target.value)} className="w-full px-4 py-3 border rounded-lg">
            {tabs.map((tab) => <option key={tab.id} value={tab.id}>{tab.label}</option>)}
          </select>
        </div>
        <div className="hidden sm:flex gap-1 overflow-x-auto pb-px">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-4 py-3 font-medium whitespace-nowrap border-b-2 -mb-px ${activeTab === tab.id ? 'text-blue-600 border-blue-600' : 'text-gray-500 hover:text-gray-700 border-transparent'}`}>
              <tab.icon className="w-4 h-4" />{tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* TAB: PERFIL (Identidade + Comunicação) */}
      {activeTab === 'perfil' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Card>
              <CardHeader title="Identidade da Marca" subtitle="Como sua empresa se apresenta" />
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Nome da Empresa</label>
                    <input type="text" value={companyName} onChange={(e) => setCompanyName(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Nicho de Atuação</label>
                    <select value={niche} onChange={(e) => setNiche(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 bg-white">
                      {niches.map((n) => <option key={n.id} value={n.id}>{n.icon} {n.name}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Descrição Curta</label>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" rows={2} placeholder="O que sua empresa faz..." />
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="Público-Alvo" subtitle="Com quem a IA está falando" />
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Quem é o cliente ideal?</label>
                  <input type="text" value={targetAudienceDesc} onChange={(e) => setTargetAudienceDesc(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="Ex: Mulheres 30+, classe A/B" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Dores e Necessidades</label>
                  <TagInput tags={painPoints} onChange={setPainPoints} placeholder="Ex: falta de tempo, medo de dentista..." />
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader title="Personalidade & Tom" subtitle="O 'jeito' da IA conversar" />
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-2">
                  {toneOptions.map((t) => (
                    <button key={t.id} onClick={() => setTone(t.id as typeof tone)} className={`p-3 border rounded-lg text-sm text-left transition-all ${tone === t.id ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : 'border-gray-200 hover:border-gray-300'}`}>
                      <span className="text-xl block mb-1">{t.icon}</span>
                      <span className="font-semibold block">{t.name}</span>
                    </button>
                  ))}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Traços de Caráter (até 4)</label>
                  <div className="flex flex-wrap gap-2">
                    {personalityOptions.map((trait) => (
                      <button key={trait.id} onClick={() => togglePersonalityTrait(trait.id)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${personalityTraits.includes(trait.id) ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                        {trait.name}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Instruções de Linguagem</label>
                  <div className="space-y-3">
                    <TagInput tags={usePhrases} onChange={setUsePhrases} placeholder="Use frases como..." />
                    <TagInput tags={avoidPhrases} onChange={setAvoidPhrases} placeholder="EVITE frases como..." />
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB: ATENDIMENTO (Distribuição + Handoff + Horário + Follow-up) */}
      {activeTab === 'atendimento' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="Distribuição & Notificação" subtitle="Para quem o lead vai?" />
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {distributionMethods.map((m) => (
                    <button key={m.id} onClick={() => setDistributionMethod(m.id)} className={`p-3 border rounded-lg text-sm text-left ${distributionMethod === m.id ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500' : 'border-gray-200 hover:border-gray-300'}`}>
                      <span className="text-xl block mb-1">{m.icon}</span>
                      <span className="font-semibold block">{m.name}</span>
                    </button>
                  ))}
                </div>
                <div className="p-3 bg-gray-50 rounded-lg space-y-3">
                  <ToggleSwitch checked={notifyManagerCopy} onChange={setNotifyManagerCopy} label="Cópia para o Gestor" description="Gestor recebe tudo" />
                  <ToggleSwitch checked={notifyBrokerRaiox} onChange={setNotifyBrokerRaiox} label="Notificar Corretor no Raio-X" />
                  {notifyBrokerRaiox && (
                    <div className="pl-4 border-l-2 border-indigo-200">
                      <label className="text-xs font-medium text-gray-500">Mínimo de mensagens para o Corretor</label>
                      <input type="number" value={minMessagesBrokerRaiox} onChange={(e) => setMinMessagesBrokerRaiox(parseInt(e.target.value))} className="w-full mt-1 px-3 py-1 text-sm border rounded" />
                    </div>
                  )}
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="Transferência (Handoff)" subtitle="Quando o humano assume?" />
              <div className="space-y-4">
                <ToggleSwitch checked={handoffEnabled} onChange={setHandoffEnabled} label="Handoff Automático" description="Transferir quando lead estiver quente" />
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">WhatsApp Gestor</label>
                    <input type="text" value={managerWhatsapp} onChange={(e) => setManagerWhatsapp(e.target.value)} className="w-full px-4 py-2 border rounded-lg text-sm" placeholder="55..." />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Máx. Mensagens</label>
                    <input type="number" value={maxMessages} onChange={(e) => setMaxMessages(parseInt(e.target.value))} className="w-full px-4 py-2 border rounded-lg text-sm" />
                  </div>
                </div>
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader title="Horário & Follow-up" subtitle="Automação fora do expediente" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-4 border-r pr-8">
                <ToggleSwitch checked={businessHoursEnabled} onChange={setBusinessHoursEnabled} label="Restringir Horário" />
                {businessHoursEnabled && (
                  <div className="grid grid-cols-1 gap-2">
                    {Object.entries(businessHours).map(([day, config]) => (
                      <div key={day} className="flex items-center justify-between text-xs py-1">
                        <span className="w-20 font-medium">{dayNames[day]}</span>
                        <div className="flex items-center gap-2">
                          <input type="checkbox" checked={config.enabled} onChange={(e) => updateBusinessHour(day, 'enabled', e.target.checked)} />
                          {config.enabled && <span className="text-gray-500">{config.open} - {config.close}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="space-y-4">
                <ToggleSwitch checked={followUpEnabled} onChange={setFollowUpEnabled} label="Follow-up Ativo" description="Reengajamento automático" />
                {followUpEnabled && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-gray-500 italic">Inatividade (h)</label>
                        <input type="number" value={followUpInactivityHours} onChange={(e) => setFollowUpInactivityHours(parseInt(e.target.value))} className="w-full px-3 py-1 text-sm border rounded" />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 italic">Intervalo (h)</label>
                        <input type="number" value={followUpIntervalHours} onChange={(e) => setFollowUpIntervalHours(parseInt(e.target.value))} className="w-full px-3 py-1 text-sm border rounded" />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB: CONHECIMENTO (FAQ + Escopo + Produtos + Diferenciais) */}
      {activeTab === 'conhecimento' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader title="Escopo de Atendimento" subtitle="O que a IA pode e não pode falar" />
                <div className="space-y-4">
                  <textarea value={scopeDescription} onChange={(e) => setScopeDescription(e.target.value)} className="w-full px-4 py-2 border rounded-lg min-h-[100px]" placeholder="Ex: Focamos apenas em vendas no litoral..." />
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-bold text-green-600 block mb-1">TÓPICOS PERMITIDOS</label>
                      <TagInput tags={allowedTopics} onChange={setAllowedTopics} placeholder="Preços, Visitas..." />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-red-600 block mb-1">TÓPICOS BLOQUEADOS</label>
                      <TagInput tags={blockedTopics} onChange={setBlockedTopics} placeholder="Política, Religião..." />
                    </div>
                  </div>
                </div>
              </Card>

              <Card>
                <CardHeader title="Base de Perguntas (FAQ)" subtitle="Respostas treinadas" />
                <div className="space-y-4">
                  <div className="max-h-[300px] overflow-y-auto space-y-2 pr-2">
                    {faqItems.map((item, i) => (
                      <div key={i} className="p-3 bg-gray-50 rounded-lg border flex justify-between gap-4">
                        <div className="text-sm">
                          <p className="font-bold text-gray-800">P: {item.question}</p>
                          <p className="text-gray-600">R: {item.answer}</p>
                        </div>
                        <button onClick={() => removeFaq(i)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    ))}
                  </div>
                  <div className="p-4 border-2 border-dashed rounded-lg bg-gray-50/50">
                    <input type="text" value={newFaqQuestion} onChange={(e) => setNewFaqQuestion(e.target.value)} className="w-full px-3 py-2 text-sm border rounded-lg mb-2" placeholder="Pergunta nova..." />
                    <textarea value={newFaqAnswer} onChange={(e) => setNewFaqAnswer(e.target.value)} className="w-full px-3 py-2 text-sm border rounded-lg mb-2" rows={2} placeholder="Sua resposta..." />
                    <button onClick={addFaq} className="w-full py-2 bg-indigo-50 text-indigo-600 font-bold rounded hover:bg-indigo-100 transition-all">+ Adicionar à Base</button>
                  </div>
                </div>
              </Card>
            </div>

            <div className="space-y-6">
              <Card>
                <CardHeader title="Catálogo & Atributos" />
                <div className="space-y-6">
                  <div>
                    <label className="text-xs font-bold text-gray-400 block mb-2 uppercase">Produtos/Serviços</label>
                    <TagInput tags={productsServices} onChange={setProductsServices} />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-gray-400 block mb-2 uppercase">Diferenciais</label>
                    <TagInput tags={differentials} onChange={setDifferentials} />
                  </div>
                  {hasProductsAccess && (
                    <div className="pt-4 border-t">
                      <button onClick={() => setActiveTab('products')} className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 text-white rounded-lg font-bold shadow-lg hover:bg-blue-700 transition-all">
                        <Package className="w-5 h-5" /> Gerenciar Imóveis
                      </button>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}

      {/* TAB: AVANÇADO (Proteções + Regras) */}
      {activeTab === 'avancado' && (
        <div className="space-y-6 max-w-4xl mx-auto">
          <Card>
            <CardHeader title="Regras de Negócio Críticas" subtitle="O que a IA NUNCA deve esquecer" />
            <div className="space-y-4">
              <TagInput tags={businessRules} onChange={setBusinessRules} placeholder="Ex: Nunca passar valor de condomínio..." />
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-100 italic text-sm text-amber-800">
                Estas regras têm prioridade máxima sobre o comportamento da IA. Use para travas de segurança.
              </div>
            </div>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="Proteção de Preços" />
              <div className="space-y-4">
                <ToggleSwitch checked={priceGuardEnabled} onChange={setPriceGuardEnabled} label="Esconder Preços" />
                {priceGuardEnabled && (
                  <select value={priceGuardBehavior} onChange={(e) => setPriceGuardBehavior(e.target.value as any)} className="w-full px-3 py-2 text-sm border rounded-lg">
                    <option value="redirect">Redirecionar para Humano</option>
                    <option value="collect_first">Coletar dados antes</option>
                  </select>
                )}
              </div>
            </Card>

            <Card>
              <CardHeader title="Coleta Obrigatória" />
              <div className="flex flex-wrap gap-2">
                {requiredInfoOptions.map((info) => (
                  <button key={info.id} onClick={() => toggleRequiredInfo(info.id)} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${requiredInfo.includes(info.id) ? 'bg-indigo-600 text-white shadow-md' : 'bg-gray-100 text-gray-500'}`}>
                    {info.name}
                  </button>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB: PRODUTOS */}
      {activeTab === 'products' && (
        <div className="space-y-4">
          <button onClick={() => setActiveTab('conhecimento')} className="flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium">
            <ChevronDown className="w-4 h-4 rotate-90" /> Voltar para Configurações
          </button>
          <ProductsTab sellers={sellers} />
        </div>
      )}
    </div>
  );
}