'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { 
  getSettings, updateSettings, 
  SettingsResponse, TenantSettings,
  ToneOption, PersonalityTrait,
  DistributionMethod, FallbackOption, NicheOption,
  RequiredInfoOption, FAQItem,
  DEFAULT_IDENTITY
} from '@/lib/settings';
import { 
  Save, Plus, X, Phone, User, MessageSquare, 
  Clock, HelpCircle, Shield, Users, RefreshCw,
  Building2, Target, Sparkles, AlertTriangle,
  CheckCircle2, Info, ChevronDown, ChevronUp
} from 'lucide-react';

// =============================================================================
// COMPONENTES AUXILIARES
// =============================================================================

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
  const [activeTab, setActiveTab] = useState('identidade');
  
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
  const [businessHours, setBusinessHours] = useState<Record<string, {open: string, close: string, enabled: boolean}>>({
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
  
  // GUARDRAILS
  const [priceGuardEnabled, setPriceGuardEnabled] = useState(true);
  const [priceGuardBehavior, setPriceGuardBehavior] = useState<'redirect' | 'collect_first' | 'allow'>('redirect');
  const [priceGuardMessage, setPriceGuardMessage] = useState('');
  const [scopeGuardEnabled, setScopeGuardEnabled] = useState(true);
  const [scopeGuardStrictness, setScopeGuardStrictness] = useState<'low' | 'medium' | 'high'>('medium');
  
  // OPTIONS
  const [niches, setNiches] = useState<NicheOption[]>([]);
  const [toneOptions, setToneOptions] = useState<ToneOption[]>([]);
  const [personalityOptions, setPersonalityOptions] = useState<PersonalityTrait[]>([]);
  const [distributionMethods, setDistributionMethods] = useState<DistributionMethod[]>([]);
  const [fallbackOptions, setFallbackOptions] = useState<FallbackOption[]>([]);
  const [requiredInfoOptions, setRequiredInfoOptions] = useState<RequiredInfoOption[]>([]);

  const dayNames: Record<string, string> = {
    monday: 'Segunda-feira', tuesday: 'Terça-feira', wednesday: 'Quarta-feira',
    thursday: 'Quinta-feira', friday: 'Sexta-feira', saturday: 'Sábado', sunday: 'Domingo',
  };

  // LOAD
  useEffect(() => {
    async function loadSettings() {
      try {
        const response = await getSettings();
        setData(response);
        const s = response.settings;
        
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
        
        // Guardrails
        const guards = s.guardrails || {};
        setPriceGuardEnabled(guards.price_guard?.enabled ?? true);
        setPriceGuardBehavior(guards.price_guard?.behavior || 'redirect');
        setPriceGuardMessage(guards.price_guard?.message || '');
        setScopeGuardEnabled(guards.scope_guard?.enabled ?? true);
        setScopeGuardStrictness(guards.scope_guard?.strictness || 'medium');
        
        // Options
        const opts = response.options || {};
        setNiches(opts.niches || []);
        setToneOptions(opts.tones || []);
        setPersonalityOptions(opts.personality_traits || []);
        setDistributionMethods(opts.distribution_methods || []);
        setFallbackOptions(opts.fallback_options || []);
        setRequiredInfoOptions(opts.required_info_options || []);
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
        distribution: { method: distributionMethod, fallback: distributionFallback, respect_daily_limit: respectDailyLimit, respect_availability: respectAvailability, notify_manager_copy: notifyManagerCopy, last_seller_index: 0 },
        guardrails: {
          price_guard: { enabled: priceGuardEnabled, behavior: priceGuardBehavior, message: priceGuardMessage },
          competitor_guard: { enabled: false, competitors: [], behavior: 'neutral' },
          scope_guard: { enabled: scopeGuardEnabled, strictness: scopeGuardStrictness },
          insist_guard: { enabled: true, max_attempts: 3, escalate_after: true },
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
    { id: 'identidade', label: 'Identidade', icon: Building2 },
    { id: 'comunicacao', label: 'Comunicação', icon: MessageSquare },
    { id: 'qualificacao', label: 'Qualificação', icon: Target },
    { id: 'distribuicao', label: 'Distribuição', icon: Users },
    { id: 'handoff', label: 'Transferência', icon: Phone },
    { id: 'horario', label: 'Horário', icon: Clock },
    { id: 'faq', label: 'FAQ', icon: HelpCircle },
    { id: 'escopo', label: 'Escopo', icon: Shield },
    { id: 'guardrails', label: 'Proteções', icon: AlertTriangle },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Configurações da IA</h1>
          <p className="text-gray-500">Configure a identidade e comportamento da sua IA atendente</p>
        </div>
        <button onClick={handleSave} disabled={saving} className="flex items-center justify-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {saving ? <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>Salvando...</> : <><Save className="w-5 h-5" />Salvar</>}
        </button>
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

      {/* TAB: IDENTIDADE */}
      {activeTab === 'identidade' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="bg-blue-100 rounded-lg p-3"><Building2 className="w-6 h-6 text-blue-600" /></div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-1">Identidade da Empresa</h2>
                <p className="text-gray-600">Quanto mais detalhes você fornecer, mais inteligente e alinhada ao seu negócio a IA será.</p>
              </div>
            </div>
          </div>

          <Card>
            <CardHeader title="Dados Básicos" subtitle="Informações essenciais" />
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nome da Empresa *</label>
                <input type="text" value={companyName} onChange={(e) => setCompanyName(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Ex: Clínica Sorrir" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nicho de Atuação *</label>
                <select value={niche} onChange={(e) => setNiche(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                  {niches.map((n) => <option key={n.id} value={n.id}>{n.icon} {n.name} - {n.description}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Descrição da Empresa</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" rows={3} placeholder="Ex: Clínica odontológica especializada em implantes..." />
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Produtos e Serviços" subtitle="O que sua empresa oferece" />
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Produtos/Serviços Oferecidos</label>
                <TagInput tags={productsServices} onChange={setProductsServices} placeholder="Ex: Implante, Clareamento..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">O que NÃO Oferecemos</label>
                <TagInput tags={notOffered} onChange={setNotOffered} placeholder="Ex: Convênios, Urgência..." />
                <p className="text-xs text-gray-500 mt-1">Evita que a IA prometa algo que você não faz</p>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Diferenciais" subtitle="O que faz sua empresa única" />
            <TagInput tags={differentials} onChange={setDifferentials} placeholder="Ex: Atendimento humanizado, 15 anos de experiência..." />
          </Card>

          <Card>
            <CardHeader title="Palavras-chave do Negócio" subtitle="Termos importantes" />
            <TagInput tags={keywords} onChange={setKeywords} placeholder="Ex: implante, prótese, faceta..." />
          </Card>

          <Card>
            <CardHeader title="Contexto Adicional" subtitle="Informações extras" />
            <textarea value={additionalContext} onChange={(e) => setAdditionalContext(e.target.value)} className="w-full px-4 py-2 border rounded-lg" rows={4} placeholder="Qualquer informação adicional..." />
          </Card>
        </div>
      )}

      {/* TAB: COMUNICAÇÃO */}
      {activeTab === 'comunicacao' && (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Tom de Voz" subtitle="Como a IA deve se comunicar" />
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Estilo Principal</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {toneOptions.map((t) => (
                    <button key={t.id} type="button" onClick={() => setTone(t.id as typeof tone)} className={`p-4 border-2 rounded-lg text-left ${tone === t.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{t.icon}</span>
                        <div><p className="font-medium">{t.name}</p><p className="text-sm text-gray-500">{t.description}</p></div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Traços de Personalidade (máx. 4)</label>
                <div className="flex flex-wrap gap-2">
                  {personalityOptions.map((trait) => (
                    <button key={trait.id} type="button" onClick={() => togglePersonalityTrait(trait.id)} disabled={!personalityTraits.includes(trait.id) && personalityTraits.length >= 4} className={`px-4 py-2 rounded-full text-sm font-medium ${personalityTraits.includes(trait.id) ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50'}`}>
                      {trait.name}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Estilo de Comunicação</label>
                <textarea value={communicationStyle} onChange={(e) => setCommunicationStyle(e.target.value)} className="w-full px-4 py-2 border rounded-lg" rows={2} placeholder="Ex: Comunicação direta mas acolhedora..." />
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Linguagem" subtitle="Palavras que a IA deve usar ou evitar" />
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Expressões Preferidas</label>
                <TagInput tags={usePhrases} onChange={setUsePhrases} placeholder="Ex: Fico feliz em ajudar..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Expressões a Evitar</label>
                <TagInput tags={avoidPhrases} onChange={setAvoidPhrases} placeholder="Ex: Infelizmente, Impossível..." />
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Público-Alvo" subtitle="Para quem a IA está conversando" />
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Descrição do Público</label>
                <input type="text" value={targetAudienceDesc} onChange={(e) => setTargetAudienceDesc(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="Ex: Mulheres 30-50 anos, classe A/B" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Segmentos de Clientes</label>
                <TagInput tags={targetSegments} onChange={setTargetSegments} placeholder="Ex: Premium, Primeira consulta..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Dores/Necessidades do Cliente</label>
                <TagInput tags={painPoints} onChange={setPainPoints} placeholder="Ex: Medo de dentista, Falta de tempo..." />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB: QUALIFICAÇÃO */}
      {activeTab === 'qualificacao' && (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Regras de Negócio" subtitle="Instruções que a IA deve seguir" />
            <div className="space-y-4">
              <TagInput tags={businessRules} onChange={setBusinessRules} placeholder="Ex: Nunca passar valores, Sempre pedir data..." />
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex gap-3">
                  <Info className="w-5 h-5 text-amber-600 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium mb-1">Exemplos:</p>
                    <ul className="list-disc list-inside text-amber-700">
                      <li>Nunca passar valores por mensagem</li>
                      <li>Sempre perguntar a cidade</li>
                      <li>Pedir fotos de referência</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Informações Obrigatórias" subtitle="Dados que a IA deve coletar" />
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {requiredInfoOptions.map((info) => (
                <button key={info.id} type="button" onClick={() => toggleRequiredInfo(info.id)} className={`p-3 border-2 rounded-lg text-left ${requiredInfo.includes(info.id) ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <p className="font-medium text-sm">{info.name}</p>
                  <p className="text-xs text-gray-500">{info.description}</p>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Perguntas Personalizadas" subtitle="Perguntas extras" />
            <TagInput tags={requiredQuestions} onChange={setRequiredQuestions} placeholder="Ex: Qual procedimento tem interesse?" />
          </Card>
        </div>
      )}

      {/* TAB: DISTRIBUIÇÃO */}
      {activeTab === 'distribuicao' && (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Distribuição de Leads" subtitle="Configure como os leads são distribuídos" />
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Método de Distribuição</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {distributionMethods.map((method) => (
                    <button key={method.id} type="button" onClick={() => setDistributionMethod(method.id)} className={`p-4 border-2 rounded-lg text-left ${distributionMethod === method.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{method.icon}</span>
                        <div><p className="font-medium">{method.name}</p><p className="text-sm text-gray-500">{method.description}</p></div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Fallback</label>
                <div className="space-y-2">
                  {fallbackOptions.map((opt) => (
                    <label key={opt.id} className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer ${distributionFallback === opt.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                      <input type="radio" name="fallback" value={opt.id} checked={distributionFallback === opt.id} onChange={(e) => setDistributionFallback(e.target.value)} className="w-4 h-4 text-blue-600" />
                      <div><p className="font-medium">{opt.name}</p><p className="text-sm text-gray-500">{opt.description}</p></div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </Card>
          <Card>
            <CardHeader title="Opções Avançadas" />
            <div className="space-y-4">
              <ToggleSwitch checked={respectDailyLimit} onChange={setRespectDailyLimit} label="Respeitar limite diário" description="Não enviar para vendedores que atingiram o limite" />
              <ToggleSwitch checked={respectAvailability} onChange={setRespectAvailability} label="Respeitar disponibilidade" description="Não enviar para vendedores indisponíveis" />
              <ToggleSwitch checked={notifyManagerCopy} onChange={setNotifyManagerCopy} label="Notificar gestor" description="Gestor recebe cópia de todas as notificações" />
            </div>
          </Card>
        </div>
      )}

      {/* TAB: HANDOFF */}
      {activeTab === 'handoff' && (
        <Card>
          <CardHeader title="Transferência para Humano" subtitle="Configure quando e para quem transferir" />
          <div className="space-y-4">
            <ToggleSwitch checked={handoffEnabled} onChange={setHandoffEnabled} label="Transferência automática" description="Transferir leads quentes automaticamente" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">WhatsApp do Gestor</label>
                <input type="text" value={managerWhatsapp} onChange={(e) => setManagerWhatsapp(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="5511999999999" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nome do Gestor</label>
                <input type="text" value={managerName} onChange={(e) => setManagerName(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="Ex: João" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Limite de mensagens</label>
              <input type="number" value={maxMessages} onChange={(e) => setMaxMessages(parseInt(e.target.value) || 15)} className="w-full px-4 py-2 border rounded-lg" min={5} max={50} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Frases que acionam transferência</label>
              <TagInput tags={handoffTriggers} onChange={setHandoffTriggers} placeholder="Ex: quero falar com humano" />
            </div>
          </div>
        </Card>
      )}

      {/* TAB: HORÁRIO */}
      {activeTab === 'horario' && (
        <Card>
          <CardHeader title="Horário de Atendimento" subtitle="Configure quando a IA deve atender" />
          <div className="space-y-4">
            <ToggleSwitch checked={businessHoursEnabled} onChange={setBusinessHoursEnabled} label="Restringir horário" description="IA só responde dentro do horário" />
            {businessHoursEnabled && (
              <>
                <div className="space-y-3">
                  {Object.entries(businessHours).map(([day, config]) => (
                    <div key={day} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                      <label className="flex items-center gap-2 w-36">
                        <input type="checkbox" checked={config.enabled} onChange={(e) => updateBusinessHour(day, 'enabled', e.target.checked)} className="w-4 h-4" />
                        <span className="text-sm">{dayNames[day]}</span>
                      </label>
                      {config.enabled && (
                        <>
                          <input type="time" value={config.open} onChange={(e) => updateBusinessHour(day, 'open', e.target.value)} className="px-2 py-1 border rounded" />
                          <span>até</span>
                          <input type="time" value={config.close} onChange={(e) => updateBusinessHour(day, 'close', e.target.value)} className="px-2 py-1 border rounded" />
                        </>
                      )}
                    </div>
                  ))}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Mensagem fora do horário</label>
                  <textarea value={outOfHoursMessage} onChange={(e) => setOutOfHoursMessage(e.target.value)} className="w-full px-4 py-2 border rounded-lg" rows={3} placeholder="Olá! No momento estamos fora do horário..." />
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      {/* TAB: FAQ */}
      {activeTab === 'faq' && (
        <Card>
          <CardHeader title="Perguntas Frequentes (FAQ)" subtitle="Respostas prontas para perguntas comuns" />
          <div className="space-y-4">
            <ToggleSwitch checked={faqEnabled} onChange={setFaqEnabled} label="FAQ ativo" description="IA usa respostas prontas quando aplicável" />
            {faqItems.map((item, i) => (
              <div key={i} className="bg-gray-50 p-4 rounded-lg">
                <div className="flex justify-between mb-2">
                  <span className="font-medium">P: {item.question}</span>
                  <button onClick={() => removeFaq(i)} className="text-red-500"><X className="w-5 h-5" /></button>
                </div>
                <p className="text-gray-600">R: {item.answer}</p>
              </div>
            ))}
            <div className="border-t pt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Nova pergunta</label>
              <input type="text" value={newFaqQuestion} onChange={(e) => setNewFaqQuestion(e.target.value)} className="w-full px-4 py-2 border rounded-lg mb-2" placeholder="Ex: Qual o horário de funcionamento?" />
              <label className="block text-sm font-medium text-gray-700 mb-2">Resposta</label>
              <textarea value={newFaqAnswer} onChange={(e) => setNewFaqAnswer(e.target.value)} className="w-full px-4 py-2 border rounded-lg mb-2" rows={2} placeholder="Ex: Funcionamos de segunda a sexta..." />
              <button onClick={addFaq} className="flex items-center gap-2 bg-gray-100 px-4 py-2 rounded-lg hover:bg-gray-200"><Plus className="w-5 h-5" /> Adicionar FAQ</button>
            </div>
          </div>
        </Card>
      )}

      {/* TAB: ESCOPO */}
      {activeTab === 'escopo' && (
        <Card>
          <CardHeader title="Escopo da IA" subtitle="Defina sobre o que a IA pode responder" />
          <div className="space-y-4">
            <ToggleSwitch checked={scopeEnabled} onChange={setScopeEnabled} label="Limitar escopo" description="IA recusa perguntas fora do contexto" />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Descrição do escopo</label>
              <textarea value={scopeDescription} onChange={(e) => setScopeDescription(e.target.value)} className="w-full px-4 py-2 border rounded-lg" rows={4} placeholder="Ex: Venda e aluguel de imóveis em São Paulo..." />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Tópicos Permitidos</label>
              <TagInput tags={allowedTopics} onChange={setAllowedTopics} placeholder="Ex: Preços, Agendamento, Localização..." />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Tópicos Bloqueados</label>
              <TagInput tags={blockedTopics} onChange={setBlockedTopics} placeholder="Ex: Política, Concorrentes..." />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Mensagem fora do escopo</label>
              <textarea value={outOfScopeMessage} onChange={(e) => setOutOfScopeMessage(e.target.value)} className="w-full px-4 py-2 border rounded-lg" rows={2} placeholder="Ex: Desculpe, não tenho informações sobre isso..." />
            </div>
          </div>
        </Card>
      )}

      {/* TAB: GUARDRAILS */}
      {activeTab === 'guardrails' && (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Proteção de Preços" subtitle="Como a IA lida com perguntas sobre valores" />
            <div className="space-y-4">
              <ToggleSwitch checked={priceGuardEnabled} onChange={setPriceGuardEnabled} label="Proteção ativa" description="IA não passa valores diretamente" />
              {priceGuardEnabled && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Comportamento</label>
                    <select value={priceGuardBehavior} onChange={(e) => setPriceGuardBehavior(e.target.value as typeof priceGuardBehavior)} className="w-full px-4 py-2 border rounded-lg">
                      <option value="redirect">Redirecionar para qualificação</option>
                      <option value="collect_first">Coletar dados antes</option>
                      <option value="allow">Permitir (dar valores)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Mensagem</label>
                    <textarea value={priceGuardMessage} onChange={(e) => setPriceGuardMessage(e.target.value)} className="w-full px-4 py-2 border rounded-lg" rows={2} placeholder="Para valores, preciso entender melhor sua necessidade..." />
                  </div>
                </>
              )}
            </div>
          </Card>
          <Card>
            <CardHeader title="Proteção de Escopo" subtitle="Rigidez da IA em manter o foco" />
            <div className="space-y-4">
              <ToggleSwitch checked={scopeGuardEnabled} onChange={setScopeGuardEnabled} label="Proteção ativa" />
              {scopeGuardEnabled && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Nível de rigidez</label>
                  <select value={scopeGuardStrictness} onChange={(e) => setScopeGuardStrictness(e.target.value as typeof scopeGuardStrictness)} className="w-full px-4 py-2 border rounded-lg">
                    <option value="low">Baixo - Mais flexível</option>
                    <option value="medium">Médio - Balanceado</option>
                    <option value="high">Alto - Bem restrito</option>
                  </select>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}