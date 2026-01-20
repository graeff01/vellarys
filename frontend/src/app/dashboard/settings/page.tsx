'use client';

// Adicionar esses imports
import ProductsTab from '@/components/dashboard/ProductsTab';
import DataSourcesTab from '@/components/dashboard/DataSourcesTab';
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
  Trash2, Package, Library, Sparkles,
  Bell, Target, Zap, Brain, Clock, Rocket, Database
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
  savePushSubscription,
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
  const [atendimentoGuidelines, setAtendimentoGuidelines] = useState('');
  const [publicoAlvoConsolidado, setPublicoAlvoConsolidado] = useState('');
  const [atendimentoStrategy, setAtendimentoStrategy] = useState<'vendedor_ativo' | 'qualificacao_inteligente' | 'agendador' | 'manual'>('qualificacao_inteligente');
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
  const [strategies, setStrategies] = useState([
    { id: 'vendedor_ativo', name: '🚀 Vendedor Ativo', description: 'IA qualifica rápido e já manda para o corretor. Ideal para fechar rápido.', icon: Rocket },
    { id: 'qualificacao_inteligente', name: '🧠 Qualificação Inteligente', description: 'A IA tira todas as dúvidas e só passa o lead quando ele estiver realmente pronto.', icon: Brain },
    { id: 'agendador', name: '📅 Agendador', description: 'O foco total da IA é marcar uma visita ou reunião com o cliente.', icon: Clock },
    { id: 'manual', name: '✋ Fluxo Manual', description: 'Você decide manualmente quando e para quem enviar cada lead.', icon: Target },
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

        // Consolidar diretrizes para a nova UI
        const traitsStr = (identity.tone_style?.personality_traits || []).join(', ');
        const useStr = (identity.tone_style?.use_phrases || []).join(', ');
        const avoidStr = (identity.tone_style?.avoid_phrases || []).join(', ');

        let guidelines = identity.additional_context || '';
        if (traitsStr) guidelines += `\nPersonalidade: ${traitsStr}`;
        if (useStr) guidelines += `\nUse frases como: ${useStr}`;
        if (avoidStr) guidelines += `\nEvite frases: ${avoidStr}`;
        setAtendimentoGuidelines(guidelines.trim());

        setTargetAudienceDesc(identity.target_audience?.description || '');
        setTargetSegments(identity.target_audience?.segments || []);
        setPainPoints(identity.target_audience?.pain_points || []);

        // Consolidar público para a nova UI
        let audience = identity.target_audience?.description || '';
        if ((identity.target_audience?.segments || []).length > 0) {
          audience += `\nSegmentos: ${(identity.target_audience?.segments || []).join(', ')}`;
        }
        if ((identity.target_audience?.pain_points || []).length > 0) {
          audience += `\nDores: ${(identity.target_audience?.pain_points || []).join(', ')}`;
        }
        setPublicoAlvoConsolidado(audience.trim());

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

        // Inferir estratégia do atendimento
        const maxMsgs = handoff.max_messages_before_handoff || 15;
        if (maxMsgs <= 2) setAtendimentoStrategy('vendedor_ativo');
        else if (maxMsgs >= 15) setAtendimentoStrategy('qualificacao_inteligente');
        else setAtendimentoStrategy('manual');

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
          tone_style: {
            tone,
            personality_traits: personalityTraits,
            communication_style: communicationStyle,
            avoid_phrases: avoidPhrases,
            use_phrases: usePhrases
          },
          target_audience: {
            description: publicoAlvoConsolidado,
            segments: targetSegments,
            pain_points: painPoints
          },
          business_rules: businessRules,
          differentials,
          keywords,
          required_questions: requiredQuestions,
          required_info: requiredInfo,
          additional_context: atendimentoGuidelines,
        },
        handoff: {
          enabled: handoffEnabled,
          manager_whatsapp: managerWhatsapp,
          manager_name: managerName,
          triggers: handoffTriggers,
          max_messages_before_handoff: atendimentoStrategy === 'vendedor_ativo' ? 2 : (atendimentoStrategy === 'qualificacao_inteligente' ? 20 : maxMessages),
          transfer_message: ''
        },
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
    { id: 'avancado', label: 'Avancado', icon: Shield },
    { id: 'datasources', label: 'Fontes de Dados', icon: Database },
  ];

  async function handleEnableNotifications() {
    const granted = await requestNotificationPermission();

    if (!granted) {
      alert('Permissão de notificações negada');
      return;
    }

    const subscription = await subscribeToPush();

    if (subscription) {
      try {
        await savePushSubscription(subscription);
        alert('Notificações ativadas com sucesso! 🎉');
      } catch (error) {
        console.error('Erro ao salvar subscription:', error);
        alert('As notificações foram habilitadas no navegador, mas houve um erro ao sincronizar com o servidor.');
      }
    } else {
      alert('Não foi possível gerar a inscrição de push. Tente recarregar a página ou verifique se as chaves VAPID estão configuradas.');
    }
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
        </div>


        {activeTab !== 'products' && activeTab !== 'datasources' && (
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

      {/* TAB: PERFIL (Identidade + Diretrizes) */}
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
                  <label className="block text-sm font-medium text-gray-700 mb-2">O que sua empresa faz?</label>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" rows={3} placeholder="Descreva brevemente seus serviços ou imóveis..." />
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="Diretrizes de Atendimento" subtitle="Instruções de comportamento para a IA" />
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Como a IA deve se comportar?</label>
                  <textarea
                    value={atendimentoGuidelines}
                    onChange={(e) => setAtendimentoGuidelines(e.target.value)}
                    className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    rows={8}
                    placeholder="Ex: Seja muito cordial e prestativo. Use emojis moderadamente. Sempre tente levar a conversa para o agendamento de uma visita. Nunca fale sobre valores de condomínio ou IPTU antes de qualificar o cliente."
                  />
                  <p className="mt-2 text-xs text-gray-400">
                    Dica: Escreva como se estivesse treinando um novo funcionário.
                  </p>
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader title="Público-Alvo" subtitle="Com quem a IA está falando" />
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Descreva seu cliente ideal</label>
                  <textarea
                    value={publicoAlvoConsolidado}
                    onChange={(e) => setPublicoAlvoConsolidado(e.target.value)}
                    className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    rows={4}
                    placeholder="Ex: Investidores em busca de rentabilidade, famílias procurando o primeiro imóvel, etc."
                  />
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="Informações Adicionais" subtitle="O que mais a IA precisa saber?" />
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Perguntas Obrigatórias</label>
                  <TagInput tags={requiredQuestions} onChange={setRequiredQuestions} placeholder="O que a IA deve perguntar?" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Conteúdo de Apoio (Contexto)</label>
                  <textarea
                    value={additionalContext}
                    onChange={(e) => setAdditionalContext(e.target.value)}
                    className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                    rows={4}
                    placeholder="Cole aqui informações extras sobre a empresa, política de preços ou links úteis."
                  />
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB: ATENDIMENTO (Estratégia + Horário + Follow-up) */}
      {activeTab === 'atendimento' && (
        <div className="space-y-6">
          <Card className="bg-blue-50/30 border-blue-100">
            <CardHeader title="Estratégia de Atendimento" subtitle="Escolha como a IA deve conduzir as conversas" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {strategies.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setAtendimentoStrategy(s.id as any)}
                  className={`p-4 border rounded-xl text-left transition-all relative ${atendimentoStrategy === s.id ? 'border-blue-600 bg-white shadow-md ring-2 ring-blue-600 ring-opacity-50' : 'border-gray-200 bg-white hover:border-blue-300'}`}
                >
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${atendimentoStrategy === s.id ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500'}`}>
                    <s.icon className="w-6 h-6" />
                  </div>
                  <p className="font-bold text-gray-900 text-sm mb-1">{s.name}</p>
                  <p className="text-xs text-gray-500 leading-relaxed">{s.description}</p>
                  {atendimentoStrategy === s.id && (
                    <div className="absolute top-2 right-2">
                      <CheckCircle2 className="w-4 h-4 text-blue-600" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-6">
              <Card>
                <CardHeader title="Configurações de Envio" subtitle="Para onde enviar o lead?" />
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">WhatsApp do Gestor</label>
                      <input type="text" value={managerWhatsapp} onChange={(e) => setManagerWhatsapp(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="Ex: 55519..." />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Nome do Gestor</label>
                      <input type="text" value={managerName} onChange={(e) => setManagerName(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="Nome para o lead" />
                    </div>
                  </div>

                  <div className="pt-4 border-t space-y-3">
                    <ToggleSwitch checked={notifyManagerCopy} onChange={setNotifyManagerCopy} label="Cópia para o Gestor" description="Receba todos os leads mesmo se atribuídos" />
                    <ToggleSwitch checked={notifyBrokerRaiox} onChange={setNotifyBrokerRaiox} label="Notificar Corretor no Raio-X" />
                    {notifyBrokerRaiox && (
                      <div className="pl-4 border-l-2 border-blue-200">
                        <label className="text-xs font-medium text-gray-500">Mínimo de mensagens para o Corretor</label>
                        <input type="number" value={minMessagesBrokerRaiox} onChange={(e) => setMinMessagesBrokerRaiox(parseInt(e.target.value))} className="w-20 px-3 py-1 text-sm border rounded ml-2" />
                      </div>
                    )}
                  </div>
                </div>
              </Card>

              <Card>
                <CardHeader title="Horário de Atendimento" subtitle="Controle quando a IA atua" />
                <div className="space-y-4">
                  <ToggleSwitch checked={businessHoursEnabled} onChange={setBusinessHoursEnabled} label="Restringir Horário" description="IA avisa que estão fora do horário" />
                  {businessHoursEnabled && (
                    <div className="space-y-3 pt-2">
                      {Object.entries(businessHours).slice(0, 5).map(([day, schedule]) => (
                        <div key={day} className="flex items-center justify-between text-sm">
                          <span className="w-20 font-medium capitalize">{dayNames[day]}</span>
                          <div className="flex items-center gap-2">
                            <input type="time" value={schedule.open} onChange={(e) => updateBusinessHour(day, 'open', e.target.value)} className="px-2 py-1 border rounded" />
                            <span>às</span>
                            <input type="time" value={schedule.close} onChange={(e) => updateBusinessHour(day, 'close', e.target.value)} className="px-2 py-1 border rounded" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            </div>

            <div className="space-y-6">
              <Card>
                <CardHeader title="Follow-up Automático" subtitle="Não deixe o lead esfriar" />
                <div className="space-y-4">
                  <ToggleSwitch checked={followUpEnabled} onChange={setFollowUpEnabled} label="Ativar Recontato" description="IA manda msg se o lead parar de responder" />
                  {followUpEnabled && (
                    <div className="space-y-4 pt-2">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">Aguardar (horas)</label>
                          <input type="number" value={followUpInactivityHours} onChange={(e) => setFollowUpInactivityHours(parseInt(e.target.value))} className="w-full px-3 py-2 border rounded-lg text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">Máximo de tentativas</label>
                          <input type="number" value={followUpMaxAttempts} onChange={(e) => setFollowUpMaxAttempts(parseInt(e.target.value))} className="w-full px-3 py-2 border rounded-lg text-sm" />
                        </div>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-2">Mensagem de Exemplo</p>
                        <p className="text-sm text-gray-600 italic">"{followUpMessages.attempt_1}"</p>
                      </div>
                    </div>
                  )}
                </div>
              </Card>

              <Card>
                <CardHeader title="Handoff (Transferência)" subtitle="Quando a IA deve parar" />
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Gatilhos de Emergência</label>
                    <TagInput tags={handoffTriggers} onChange={setHandoffTriggers} placeholder="Ex: falar com humano, reclamar..." />
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
      {/* TAB: CONHECIMENTO */}
      {activeTab === 'conhecimento' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Card>
              <CardHeader title="Base de Perguntas (FAQ)" subtitle="Respostas treinadas para dúvidas comuns" />
              <div className="space-y-4">
                <div className="max-h-[400px] overflow-y-auto space-y-2 pr-2">
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
                <div className="p-4 border-2 border-dashed rounded-lg bg-indigo-50/10">
                  <input type="text" value={newFaqQuestion} onChange={(e) => setNewFaqQuestion(e.target.value)} className="w-full px-3 py-2 text-sm border rounded-lg mb-2" placeholder="Pergunta que o cliente faz..." />
                  <textarea value={newFaqAnswer} onChange={(e) => setNewFaqAnswer(e.target.value)} className="w-full px-3 py-2 text-sm border rounded-lg mb-2" rows={2} placeholder="Sua resposta memorizada..." />
                  <button onClick={addFaq} className="w-full py-2 bg-indigo-600 text-white font-bold rounded hover:bg-indigo-700 transition-all">+ Adicionar à Base</button>
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader title="Catálogo de Ofertas" subtitle="O que você vende ou aluga" />
              <div className="space-y-6">
                <div>
                  <label className="text-xs font-bold text-gray-400 block mb-2 uppercase">Produtos/Serviços</label>
                  <TagInput tags={productsServices} onChange={setProductsServices} />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-400 block mb-2 uppercase">Nossos Diferenciais</label>
                  <TagInput tags={differentials} onChange={setDifferentials} />
                </div>
                {hasProductsAccess && (
                  <div className="pt-4 border-t">
                    <button onClick={() => setActiveTab('products')} className="w-full flex items-center justify-center gap-2 py-4 bg-indigo-600 text-white rounded-xl font-bold shadow-lg hover:bg-indigo-700 transition-all">
                      <Package className="w-5 h-5" /> Gerenciar Detalhes dos Imóveis
                    </button>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB: AVANÇADO */}
      {activeTab === 'avancado' && (
        <div className="space-y-6 max-w-4xl mx-auto">
          <Card className="bg-indigo-50/50 border-indigo-100">
            <CardHeader
              title="Notificações do Sistema"
              subtitle="Receba alertas de novos leads diretamente no celular"
            />
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 p-2">
              <div className="text-sm text-indigo-900">
                <p className="font-bold mb-1">Passo a passo para iPhone:</p>
                <ol className="list-decimal ml-4 space-y-1">
                  <li>Compartilhar &rarr; "Adicionar à Tela de Início"</li>
                  <li>Abra o App pela tela inicial e ative aqui:</li>
                </ol>
              </div>
              <button
                onClick={handleEnableNotifications}
                className="flex items-center justify-center gap-2 bg-indigo-600 text-white px-8 py-4 rounded-xl font-bold hover:bg-indigo-700 shadow-xl transition-all"
              >
                <Bell className="w-6 h-6" /> Ativar Push Notifications
              </button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Regras de Ouro" subtitle="O que a IA NUNCA deve fazer ou dizer" />
            <div className="space-y-4">
              <TagInput tags={businessRules} onChange={setBusinessRules} placeholder="Ex: Nunca falar sobre parcerias, nunca dar descontos..." />
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-100 italic text-sm text-amber-800">
                Estas regras têm prioridade total. A IA será proibida de descumprir estes itens.
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Coleta de Dados" subtitle="O que é obrigatório perguntar?" />
            <div className="flex flex-wrap gap-2">
              {requiredInfoOptions.map((info) => (
                <button key={info.id} onClick={() => toggleRequiredInfo(info.id)} className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${requiredInfo.includes(info.id) ? 'bg-indigo-600 text-white shadow-md' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}>
                  {info.name}
                </button>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* TAB: PRODUTOS */}
      {activeTab === 'products' && (
        <div className="space-y-4">
          <button onClick={() => setActiveTab('conhecimento')} className="flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium">
            <ChevronDown className="w-4 h-4 rotate-90" /> Voltar para Configuracoes
          </button>
          <ProductsTab sellers={sellers} />
        </div>
      )}

      {/* TAB: FONTES DE DADOS */}
      {activeTab === 'datasources' && (
        <DataSourcesTab />
      )}
    </div>
  );
}