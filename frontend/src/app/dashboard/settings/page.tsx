'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { 
  getSettings, updateSettings, SettingsResponse, 
  DistributionMethod, FallbackOption 
} from '@/lib/settings';
import { 
  Save, Plus, X, Phone, User, MessageSquare, 
  Clock, HelpCircle, Shield, Users, RefreshCw
} from 'lucide-react';

export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState('empresa');
  
  // Form state - Empresa
  const [companyName, setCompanyName] = useState('');
  const [niche, setNiche] = useState('');
  const [tone, setTone] = useState('cordial');
  
  // Handoff
  const [managerWhatsapp, setManagerWhatsapp] = useState('');
  const [managerName, setManagerName] = useState('');
  const [handoffEnabled, setHandoffEnabled] = useState(true);
  const [handoffTriggers, setHandoffTriggers] = useState<string[]>([]);
  const [newTrigger, setNewTrigger] = useState('');
  const [maxMessages, setMaxMessages] = useState(15);
  
  // Horário
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
  const [faqItems, setFaqItems] = useState<Array<{question: string, answer: string}>>([]);
  const [newFaqQuestion, setNewFaqQuestion] = useState('');
  const [newFaqAnswer, setNewFaqAnswer] = useState('');
  
  // Escopo
  const [scopeEnabled, setScopeEnabled] = useState(true);
  const [scopeDescription, setScopeDescription] = useState('');
  const [outOfScopeMessage, setOutOfScopeMessage] = useState('');
  
  // Distribuição
  const [distributionMethod, setDistributionMethod] = useState('round_robin');
  const [distributionFallback, setDistributionFallback] = useState('manager');
  const [respectDailyLimit, setRespectDailyLimit] = useState(true);
  const [respectAvailability, setRespectAvailability] = useState(true);
  const [notifyManagerCopy, setNotifyManagerCopy] = useState(false);
  const [distributionMethods, setDistributionMethods] = useState<DistributionMethod[]>([]);
  const [fallbackOptions, setFallbackOptions] = useState<FallbackOption[]>([]);
  
  // Personalização
  const [customQuestions, setCustomQuestions] = useState<string[]>([]);
  const [customRules, setCustomRules] = useState<string[]>([]);
  const [newQuestion, setNewQuestion] = useState('');
  const [newRule, setNewRule] = useState('');

  const dayNames: Record<string, string> = {
    monday: 'Segunda-feira',
    tuesday: 'Terça-feira',
    wednesday: 'Quarta-feira',
    thursday: 'Quinta-feira',
    friday: 'Sexta-feira',
    saturday: 'Sábado',
    sunday: 'Domingo',
  };

  useEffect(() => {
    async function loadSettings() {
      try {
        const response = await getSettings();
        setData(response);
        const s = response.settings;
        
        setCompanyName(s.company_name || response.tenant.name);
        setNiche(s.niche || 'services');
        setTone(s.tone || 'cordial');
        setManagerWhatsapp(s.manager_whatsapp || '');
        setManagerName(s.manager_name || '');
        setHandoffEnabled(s.handoff_enabled ?? true);
        setHandoffTriggers(s.handoff_triggers || []);
        setMaxMessages(s.max_messages_before_handoff || 15);
        setBusinessHoursEnabled(s.business_hours_enabled || false);
        if (s.business_hours) setBusinessHours(s.business_hours);
        setOutOfHoursMessage(s.out_of_hours_message || '');
        setFaqEnabled(s.faq_enabled ?? true);
        setFaqItems(s.faq_items || []);
        setScopeEnabled(s.scope_enabled ?? true);
        setScopeDescription(s.scope_description || '');
        setOutOfScopeMessage(s.out_of_scope_message || '');
        setCustomQuestions(s.custom_questions || []);
        setCustomRules(s.custom_rules || []);
        
        // Distribuição
        const dist = s.distribution || {};
        setDistributionMethod(dist.method || 'round_robin');
        setDistributionFallback(dist.fallback || 'manager');
        setRespectDailyLimit(dist.respect_daily_limit ?? true);
        setRespectAvailability(dist.respect_availability ?? true);
        setNotifyManagerCopy(dist.notify_manager_copy ?? false);
        
        // Opções de distribuição
        setDistributionMethods(response.distribution_methods || []);
        setFallbackOptions(response.fallback_options || []);
      } catch (error) {
        console.error('Erro ao carregar configurações:', error);
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  async function handleSave() {
    setSaving(true);
    setSuccess(false);
    try {
      await updateSettings({
        name: companyName,
        company_name: companyName,
        niche,
        tone,
        manager_whatsapp: managerWhatsapp,
        manager_name: managerName,
        handoff_enabled: handoffEnabled,
        handoff_triggers: handoffTriggers,
        max_messages_before_handoff: maxMessages,
        business_hours_enabled: businessHoursEnabled,
        business_hours: businessHours,
        out_of_hours_message: outOfHoursMessage,
        faq_enabled: faqEnabled,
        faq_items: faqItems,
        scope_enabled: scopeEnabled,
        scope_description: scopeDescription,
        out_of_scope_message: outOfScopeMessage,
        custom_questions: customQuestions,
        custom_rules: customRules,
        distribution: {
          method: distributionMethod,
          fallback: distributionFallback,
          respect_daily_limit: respectDailyLimit,
          respect_availability: respectAvailability,
          notify_manager_copy: notifyManagerCopy,
          last_seller_index: 0,
        },
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (error) {
      console.error('Erro ao salvar:', error);
      alert('Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  }

  // Helpers para listas
  const addToList = (list: string[], setList: (l: string[]) => void, value: string, setValue: (v: string) => void) => {
    if (value.trim()) {
      setList([...list, value.trim()]);
      setValue('');
    }
  };

  const removeFromList = (list: string[], setList: (l: string[]) => void, index: number) => {
    setList(list.filter((_, i) => i !== index));
  };

  function addFaq() {
    if (newFaqQuestion.trim() && newFaqAnswer.trim()) {
      setFaqItems([...faqItems, { question: newFaqQuestion.trim(), answer: newFaqAnswer.trim() }]);
      setNewFaqQuestion('');
      setNewFaqAnswer('');
    }
  }

  function removeFaq(index: number) {
    setFaqItems(faqItems.filter((_, i) => i !== index));
  }

  function updateBusinessHour(day: string, field: 'open' | 'close' | 'enabled', value: string | boolean) {
    setBusinessHours({
      ...businessHours,
      [day]: { ...businessHours[day], [field]: value }
    });
  }

  if (loading) {
    return <div className="text-center py-8 text-gray-500">Carregando...</div>;
  }

  const tabs = [
    { id: 'empresa', label: 'Empresa', icon: User },
    { id: 'distribuicao', label: 'Distribuição', icon: Users },
    { id: 'reengajamento', label: 'Reengajamento', icon: RefreshCw },
    { id: 'handoff', label: 'Transferência', icon: Phone },
    { id: 'horario', label: 'Horário', icon: Clock },
    { id: 'faq', label: 'FAQ', icon: HelpCircle },
    { id: 'escopo', label: 'Escopo', icon: Shield },
    { id: 'personalizar', label: 'Personalizar', icon: MessageSquare },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Configurações</h1>
          <p className="text-gray-500">Configure sua IA atendente</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <Save className="w-5 h-5" />
          {saving ? 'Salvando...' : 'Salvar'}
        </button>
      </div>

      {success && (
        <div className="bg-green-50 text-green-600 p-4 rounded-lg">
          Configurações salvas com sucesso!
        </div>
      )}

      {/* Tabs - Responsivas */}
      <div className="border-b">
        {/* Mobile: Select dropdown */}
        <div className="sm:hidden">
          <select
            value={activeTab}
            onChange={(e) => setActiveTab(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 font-medium focus:ring-2 focus:ring-blue-500"
          >
            {tabs.map((tab) => (
              <option key={tab.id} value={tab.id}>
                {tab.label}
              </option>
            ))}
          </select>
        </div>
        
        {/* Desktop: Tabs horizontais */}
        <div className="hidden sm:flex gap-1 overflow-x-auto pb-px">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
                activeTab === tab.id
                  ? 'text-blue-600 border-blue-600'
                  : 'text-gray-500 hover:text-gray-700 border-transparent'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        
        {/* EMPRESA */}
        {activeTab === 'empresa' && (
          <Card>
            <CardHeader title="Dados da Empresa" subtitle="Informações básicas do seu negócio" />
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nome da Empresa</label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nicho de Atuação</label>
                <select
                  value={niche}
                  onChange={(e) => setNiche(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  {data?.available_niches.map((n) => (
                    <option key={n.id} value={n.id}>{n.name} - {n.description}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tom de Voz da IA</label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="formal">Formal - Profissional e direto</option>
                  <option value="cordial">Cordial - Amigável e educado</option>
                  <option value="informal">Informal - Descontraído e próximo</option>
                </select>
              </div>
            </div>
          </Card>
        )}

        {/* DISTRIBUIÇÃO */}
        {activeTab === 'distribuicao' && (
          <>
            <Card>
              <CardHeader 
                title="Distribuição de Leads" 
                subtitle="Configure como os leads são distribuídos para sua equipe" 
              />
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Método de Distribuição
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {distributionMethods.map((method) => (
                      <button
                        key={method.id}
                        type="button"
                        onClick={() => setDistributionMethod(method.id)}
                        className={`p-4 border-2 rounded-lg text-left transition-all ${
                          distributionMethod === method.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{method.icon}</span>
                          <div>
                            <p className="font-medium text-gray-900">{method.name}</p>
                            <p className="text-sm text-gray-500">{method.description}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Quando não encontrar vendedor compatível
                  </label>
                  <div className="space-y-2">
                    {fallbackOptions.map((option) => (
                      <label
                        key={option.id}
                        className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-all ${
                          distributionFallback === option.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <input
                          type="radio"
                          name="fallback"
                          value={option.id}
                          checked={distributionFallback === option.id}
                          onChange={(e) => setDistributionFallback(e.target.value)}
                          className="w-4 h-4 text-blue-600"
                        />
                        <div>
                          <p className="font-medium text-gray-900">{option.name}</p>
                          <p className="text-sm text-gray-500">{option.description}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="Opções Avançadas" subtitle="Configurações adicionais de distribuição" />
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">Respeitar limite diário</p>
                    <p className="text-sm text-gray-500">Não enviar leads para vendedores que atingiram o limite do dia</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={respectDailyLimit} 
                      onChange={(e) => setRespectDailyLimit(e.target.checked)} 
                      className="sr-only peer" 
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">Respeitar disponibilidade</p>
                    <p className="text-sm text-gray-500">Não enviar leads para vendedores indisponíveis ou de férias</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={respectAvailability} 
                      onChange={(e) => setRespectAvailability(e.target.checked)} 
                      className="sr-only peer" 
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">Notificar gestor em todas as atribuições</p>
                    <p className="text-sm text-gray-500">Gestor recebe cópia de todas as notificações de leads</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={notifyManagerCopy} 
                      onChange={(e) => setNotifyManagerCopy(e.target.checked)} 
                      className="sr-only peer" 
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </div>
            </Card>
          </>
        )}

        {/* HANDOFF */}
        {activeTab === 'handoff' && (
          <Card>
            <CardHeader title="Transferência para Humano" subtitle="Configure quando e para quem a IA deve transferir" />
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Transferência automática</p>
                  <p className="text-sm text-gray-500">Transferir leads quentes automaticamente</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={handoffEnabled} onChange={(e) => setHandoffEnabled(e.target.checked)} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">WhatsApp do Gestor</label>
                <input type="text" value={managerWhatsapp} onChange={(e) => setManagerWhatsapp(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg" placeholder="5511999999999" />
                <p className="text-xs text-gray-500 mt-1">Usado quando nenhum vendedor está disponível ou distribuição manual</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nome do Gestor</label>
                <input type="text" value={managerName} onChange={(e) => setManagerName(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg" placeholder="Ex: João" />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Limite de mensagens</label>
                <input type="number" value={maxMessages} onChange={(e) => setMaxMessages(parseInt(e.target.value) || 15)} className="w-full px-4 py-2 border border-gray-300 rounded-lg" min={5} max={50} />
                <p className="text-xs text-gray-500 mt-1">Após este número de mensagens, a IA transfere automaticamente</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Frases que acionam transferência</label>
                {handoffTriggers.map((t, i) => (
                  <div key={i} className="flex items-center gap-2 bg-gray-50 p-3 rounded-lg mb-2">
                    <span className="flex-1">&quot;{t}&quot;</span>
                    <button onClick={() => removeFromList(handoffTriggers, setHandoffTriggers, i)} className="text-red-500"><X className="w-5 h-5" /></button>
                  </div>
                ))}
                <div className="flex gap-2">
                  <input type="text" value={newTrigger} onChange={(e) => setNewTrigger(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && addToList(handoffTriggers, setHandoffTriggers, newTrigger, setNewTrigger)} className="flex-1 px-4 py-2 border border-gray-300 rounded-lg" placeholder="Ex: quero falar com humano" />
                  <button onClick={() => addToList(handoffTriggers, setHandoffTriggers, newTrigger, setNewTrigger)} className="flex items-center gap-2 bg-gray-100 px-4 py-2 rounded-lg hover:bg-gray-200"><Plus className="w-5 h-5" /></button>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* HORÁRIO */}
        {activeTab === 'horario' && (
          <Card>
            <CardHeader title="Horário de Atendimento" subtitle="Configure quando a IA deve atender" />
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Restringir horário</p>
                  <p className="text-sm text-gray-500">IA só responde dentro do horário configurado</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={businessHoursEnabled} onChange={(e) => setBusinessHoursEnabled(e.target.checked)} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

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
                    <textarea value={outOfHoursMessage} onChange={(e) => setOutOfHoursMessage(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg" rows={3} placeholder="Olá! No momento estamos fora do horário de atendimento..." />
                  </div>
                </>
              )}
            </div>
          </Card>
        )}

        {/* FAQ */}
        {activeTab === 'faq' && (
          <Card>
            <CardHeader title="Perguntas Frequentes (FAQ)" subtitle="Respostas prontas para perguntas comuns" />
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">FAQ ativo</p>
                  <p className="text-sm text-gray-500">IA usa respostas prontas quando aplicável</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={faqEnabled} onChange={(e) => setFaqEnabled(e.target.checked)} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              {faqItems.map((item, i) => (
                <div key={i} className="bg-gray-50 p-4 rounded-lg">
                  <div className="flex justify-between mb-2">
                    <span className="font-medium text-gray-900">P: {item.question}</span>
                    <button onClick={() => removeFaq(i)} className="text-red-500"><X className="w-5 h-5" /></button>
                  </div>
                  <p className="text-gray-600">R: {item.answer}</p>
                </div>
              ))}

              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Nova pergunta</label>
                <input type="text" value={newFaqQuestion} onChange={(e) => setNewFaqQuestion(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-2" placeholder="Ex: Qual o horário de funcionamento?" />
                <label className="block text-sm font-medium text-gray-700 mb-2">Resposta</label>
                <textarea value={newFaqAnswer} onChange={(e) => setNewFaqAnswer(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-2" rows={2} placeholder="Ex: Funcionamos de segunda a sexta, das 8h às 18h." />
                <button onClick={addFaq} className="flex items-center gap-2 bg-gray-100 px-4 py-2 rounded-lg hover:bg-gray-200"><Plus className="w-5 h-5" /> Adicionar FAQ</button>
              </div>
            </div>
          </Card>
        )}

        {/* ESCOPO */}
        {activeTab === 'escopo' && (
          <Card>
            <CardHeader title="Escopo da IA" subtitle="Defina sobre o que a IA pode responder" />
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Limitar escopo</p>
                  <p className="text-sm text-gray-500">IA recusa perguntas fora do contexto</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={scopeEnabled} onChange={(e) => setScopeEnabled(e.target.checked)} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Descrição do escopo</label>
                <textarea value={scopeDescription} onChange={(e) => setScopeDescription(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg" rows={4} placeholder="Ex: Venda e aluguel de imóveis em São Paulo. Apartamentos, casas e salas comerciais. Financiamento e documentação." />
                <p className="text-xs text-gray-500 mt-1">Descreva os assuntos que a IA pode responder</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Mensagem fora do escopo</label>
                <textarea value={outOfScopeMessage} onChange={(e) => setOutOfScopeMessage(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg" rows={2} placeholder="Ex: Desculpe, não tenho informações sobre isso. Posso ajudar com dúvidas sobre nossos imóveis!" />
              </div>
            </div>
          </Card>
        )}

        {/* PERSONALIZAR */}
        {activeTab === 'personalizar' && (
          <>
            <Card>
              <CardHeader title="Perguntas Personalizadas" subtitle="Perguntas extras que a IA deve fazer" />
              <div className="space-y-4">
                {customQuestions.map((q, i) => (
                  <div key={i} className="flex items-center gap-2 bg-gray-50 p-3 rounded-lg">
                    <span className="flex-1">{q}</span>
                    <button onClick={() => removeFromList(customQuestions, setCustomQuestions, i)} className="text-red-500"><X className="w-5 h-5" /></button>
                  </div>
                ))}
                <div className="flex gap-2">
                  <input type="text" value={newQuestion} onChange={(e) => setNewQuestion(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && addToList(customQuestions, setCustomQuestions, newQuestion, setNewQuestion)} className="flex-1 px-4 py-2 border border-gray-300 rounded-lg" placeholder="Ex: Qual seu horário de preferência?" />
                  <button onClick={() => addToList(customQuestions, setCustomQuestions, newQuestion, setNewQuestion)} className="flex items-center gap-2 bg-gray-100 px-4 py-2 rounded-lg hover:bg-gray-200"><Plus className="w-5 h-5" /></button>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="Regras Personalizadas" subtitle="Instruções específicas para a IA" />
              <div className="space-y-4">
                {customRules.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 bg-gray-50 p-3 rounded-lg">
                    <span className="flex-1">{r}</span>
                    <button onClick={() => removeFromList(customRules, setCustomRules, i)} className="text-red-500"><X className="w-5 h-5" /></button>
                  </div>
                ))}
                <div className="flex gap-2">
                  <input type="text" value={newRule} onChange={(e) => setNewRule(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && addToList(customRules, setCustomRules, newRule, setNewRule)} className="flex-1 px-4 py-2 border border-gray-300 rounded-lg" placeholder="Ex: Sempre mencionar estacionamento gratuito" />
                  <button onClick={() => addToList(customRules, setCustomRules, newRule, setNewRule)} className="flex items-center gap-2 bg-gray-100 px-4 py-2 rounded-lg hover:bg-gray-200"><Plus className="w-5 h-5" /></button>
                </div>
              </div>
            </Card>
          </>
        )}
        
        {/* REENGAJAMENTO */}
        {activeTab === 'reengajamento' && (
          <Card>
            <CardHeader 
              title="Reengajamento de Leads" 
              subtitle="Recupere leads inativos automaticamente" 
            />
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  <strong>Como funciona:</strong> Quando um lead para de responder, a IA envia 
                  automaticamente uma mensagem de follow-up para tentar recuperá-lo.
                </p>
              </div>
              
              <div className="text-center py-8">
                <RefreshCw className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-4">
                  Configure o reengajamento automático de leads
                </p>
                <a
                  href="/dashboard/settings/reengagement"
                  className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
                >
                  <RefreshCw className="w-5 h-5" />
                  Configurar Reengajamento
                </a>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}