'use client';

import { useState, useRef, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { getToken, getUser } from '@/lib/auth';
import {
  Bot, Send, Trash2, Sparkles, Loader2, User,
  MessageSquare, Zap, ThermometerSun, Info,
  AlertTriangle, CheckCircle2, ChevronRight, Settings, ChevronDown
} from 'lucide-react';
import { FeatureGate } from '@/components/FeatureGate';

declare const process: any;

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface SimulatorMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sentiment?: string;
  qualificationHint?: string;
}

interface SuggestionCategory {
  category: string;
  messages: string[];
}

export default function SimulatorPage() {
  return (
    <FeatureGate feature="simulator_enabled">
      <Suspense fallback={<div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 animate-spin text-purple-600" /></div>}>
        <SimulatorContent />
      </Suspense>
    </FeatureGate>
  );
}

function SimulatorContent() {
  const searchParams = useSearchParams();
  const targetTenantId = searchParams.get('target_tenant_id');
  const user = getUser();
  const isSuperAdmin = user?.role === 'superadmin';

  const [messages, setMessages] = useState<SimulatorMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const [sessionId] = useState(() => `sim_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const [lastSentiment, setLastSentiment] = useState<string>('neutral');
  const [lastQualification, setLastQualification] = useState<string>('');
  const [suggestions, setSuggestions] = useState<SuggestionCategory[]>([]);
  const [tenantName, setTenantName] = useState<string>('');
  const [availableTenants, setAvailableTenants] = useState<any[]>([]);
  const [showTenantSelector, setShowTenantSelector] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function fetchTenants() {
      if (!isSuperAdmin) return;
      try {
        const token = getToken();
        const response = await fetch(`${API_URL}/admin/tenants`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setAvailableTenants(data.tenants || []);
        }
      } catch (error) {
        console.error('Error fetching tenants:', error);
      }
    }
    fetchTenants();
  }, [isSuperAdmin]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load suggestions
  useEffect(() => {
    async function fetchSuggestions() {
      try {
        const token = getToken();
        const url = new URL(`${API_URL}/simulator/suggestions`);
        if (targetTenantId) url.searchParams.append('target_tenant_id', targetTenantId);

        const response = await fetch(url.toString(), {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setSuggestions(data.suggestions || []);
        }
      } catch (error) {
        console.error('Error fetching suggestions:', error);
      }
    }
    fetchSuggestions();
  }, [targetTenantId]);

  // Fetch Tenant Name if in Masquerade mode
  useEffect(() => {
    async function fetchTenantName() {
      if (!targetTenantId) return;
      try {
        const token = getToken();
        // Since we don't have a direct public "get tenant name" endpoint easily accessible without auth complex,
        // we can reuse the /admin/tenants endpoint if superadmin, or just fetch from settings/profile context if possible.
        // For now, let's try to get it from the settings endpoint which supports masquerading.
        const response = await fetch(`${API_URL}/settings?target_tenant_id=${targetTenantId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setTenantName(data.tenant?.name || `ID: ${targetTenantId}`);
        }
      } catch (error) {
        console.error('Error fetching tenant name:', error);
      }
    }
    if (isSuperAdmin && targetTenantId) {
      fetchTenantName();
    }
  }, [targetTenantId, isSuperAdmin]);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const userMessage: SimulatorMessage = {
      id: Date.now(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const token = getToken();
      const url = new URL(`${API_URL}/simulator/chat`);
      if (targetTenantId) url.searchParams.append('target_tenant_id', targetTenantId);

      const response = await fetch(url.toString(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
          history: messages.map(m => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (response.ok) {
        const data = await response.json();

        // Simular delay de digitação
        const typingDelay = data.typing_delay || 1.5;
        await new Promise(resolve => setTimeout(resolve, typingDelay * 1000));

        const assistantMessage: SimulatorMessage = {
          id: Date.now(),
          role: 'assistant',
          content: data.reply,
          timestamp: new Date(),
          sentiment: data.sentiment,
          qualificationHint: data.qualification_hint,
        };

        setMessages(prev => [...prev, assistantMessage]);
        setLastSentiment(data.sentiment);
        setLastQualification(data.qualification_hint);
      } else {
        const error = await response.json();
        const errorMessage: SimulatorMessage = {
          id: Date.now(),
          role: 'assistant',
          content: `❌ Erro: ${error.detail || 'Não foi possível processar a mensagem'}`,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Erro no simulador:', error);
      const errorMessage: SimulatorMessage = {
        id: Date.now(),
        role: 'assistant',
        content: '❌ Erro de conexão. Verifique se o backend está rodando.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  function clearChat() {
    setMessages([]);
    setLastSentiment('neutral');
    setLastQualification('');
  }

  const sentimentColors: Record<string, { bg: string; text: string; label: string }> = {
    frustrated: { bg: 'bg-red-100', text: 'text-red-700', label: '😤 Frustrado' },
    urgent: { bg: 'bg-orange-100', text: 'text-orange-700', label: '⚡ Urgente' },
    excited: { bg: 'bg-green-100', text: 'text-green-700', label: '🎉 Animado' },
    positive: { bg: 'bg-blue-100', text: 'text-blue-700', label: '😊 Positivo' },
    neutral: { bg: 'bg-gray-100', text: 'text-gray-700', label: '😐 Neutro' },
  };

  const currentSentiment = sentimentColors[lastSentiment] || sentimentColors.neutral;

  return (
    <div className="space-y-6">
      {/* SuperAdmin Banner */}
      {isSuperAdmin && targetTenantId && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-xl flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-500">
          <div className="flex items-center gap-4">
            <div className="bg-amber-100 p-2 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h4 className="text-amber-900 font-bold uppercase text-xs tracking-wider">Modo Demonstração Ativo</h4>
              <p className="text-amber-700 text-sm">
                Você está simulando o atendimento para o cliente <span className="font-bold underline">{tenantName || `ID: ${targetTenantId}`}</span>.
              </p>
            </div>
          </div>
          <a
            href={`/dashboard/settings?target_tenant_id=${targetTenantId}`}
            className="flex items-center gap-2 px-3 py-1.5 bg-amber-100 hover:bg-amber-200 text-amber-800 rounded-lg text-sm font-medium transition-colors"
          >
            <Settings className="w-4 h-4" />
            Configurações
          </a>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl shadow-lg shadow-purple-200">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              Simulador Live
            </h1>
            <p className="text-gray-500 mt-1">
              {targetTenantId ? 'Ambiente de demonstração personalizada' : 'Teste como sua IA vai responder aos clientes'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all border border-transparent hover:border-red-100"
              >
                Resetar Conversa
              </button>
            )}
          </div>
        </div>

        {/* Seletor de Cliente (Apenas SuperAdmin) */}
        {isSuperAdmin && (
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between group animate-in fade-in slide-in-from-top-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                <User className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Cliente Selecionado</p>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900">
                    {targetTenantId ? (availableTenants.find(t => t.id === parseInt(targetTenantId))?.name || `ID: ${targetTenantId}`) : 'Selecione um cliente para simular'}
                  </h3>
                </div>
              </div>
            </div>

            <div className="relative">
              <button
                onClick={() => setShowTenantSelector(!showTenantSelector)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm font-medium transition-colors border border-gray-100"
              >
                Trocar Cliente
                <ChevronDown className={`w-4 h-4 transition-transform ${showTenantSelector ? 'rotate-180' : ''}`} />
              </button>

              {showTenantSelector && (
                <div className="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-xl shadow-xl z-50 py-2 animate-in fade-in slide-in-from-top-2">
                  <div className="px-3 pb-2 mb-2 border-b border-gray-100">
                    <p className="text-[10px] font-bold text-gray-400 uppercase">Disponíveis para Simulação</p>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    {availableTenants
                      .filter(t => t.id !== user?.tenant_id)
                      .map((tenant) => (
                        <button
                          key={tenant.id}
                          onClick={() => {
                            const url = new URL(window.location.href);
                            url.searchParams.set('target_tenant_id', tenant.id.toString());
                            window.location.href = url.pathname + url.search;
                          }}
                          className={`w-full text-left px-4 py-2 text-sm hover:bg-blue-50 flex items-center justify-between ${targetTenantId === tenant.id.toString() ? 'bg-blue-50 text-blue-700 font-bold' : 'text-gray-700'}`}
                        >
                          {tenant.name}
                          {targetTenantId === tenant.id.toString() && <CheckCircle2 className="w-4 h-4" />}
                        </button>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Layout Principal */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* Chat - Ocupa 3 colunas */}
        <div className="lg:col-span-3">
          <Card className="flex flex-col h-[calc(100vh-250px)] min-h-[500px]">
            {/* Header do Chat */}
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-purple-500" />
                <h3 className="font-semibold text-gray-900">Conversa de Teste</h3>
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                  {messages.length} msgs
                </span>
              </div>
              {messages.length > 0 && (
                <button
                  onClick={clearChat}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Limpar
                </button>
              )}
            </div>

            {/* Área de Mensagens */}
            <div
              className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50"
              style={{ scrollbarWidth: 'thin' }}
            >
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
                  <div className="w-20 h-20 bg-gradient-to-br from-purple-100 to-blue-100 rounded-full flex items-center justify-center">
                    <Bot className="w-10 h-10 text-purple-500" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-gray-600">Comece uma conversa de teste</p>
                    <p className="text-sm text-gray-400 mt-1">
                      Digite uma mensagem como um cliente faria
                    </p>
                  </div>

                  {/* Categorias de Sugestões Dinâmicas */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-4xl mt-6 px-4">
                    {suggestions.length > 0 ? (
                      suggestions.slice(0, 4).map((cat, idx) => (
                        <div key={idx} className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                            <ChevronRight className="w-3 h-3 text-purple-400" />
                            {cat.category}
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {cat.messages.slice(0, 3).map((msg: string, mIdx: number) => (
                              <button
                                key={mIdx}
                                onClick={() => setInput(msg)}
                                className="text-left px-3 py-1.5 text-xs bg-gray-50 hover:bg-purple-50 hover:text-purple-700 rounded-lg transition-colors border border-transparent hover:border-purple-100"
                              >
                                {msg}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-2 text-center py-8 bg-white rounded-2xl border border-dashed border-gray-200">
                        <Loader2 className="w-6 h-6 animate-spin text-gray-300 mx-auto mb-2" />
                        <p className="text-xs text-gray-400">Carregando sugestões personalizadas...</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'assistant' ? 'justify-start' : 'justify-end'}`}
                  >
                    {/* Avatar IA */}
                    {msg.role === 'assistant' && (
                      <div className="flex-shrink-0 mr-2">
                        <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-sm">
                          <Bot className="w-4 h-4 text-white" />
                        </div>
                      </div>
                    )}

                    {/* Balão */}
                    <div
                      className={`max-w-[80%] px-4 py-3 rounded-2xl ${msg.role === 'assistant'
                        ? 'bg-white text-gray-800 border border-gray-200 rounded-tl-md shadow-sm'
                        : 'bg-blue-600 text-white rounded-tr-md shadow-sm'
                        }`}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </p>
                      <p className={`text-xs mt-1.5 ${msg.role === 'assistant' ? 'text-gray-400' : 'text-blue-200'
                        }`}>
                        {msg.timestamp.toLocaleTimeString('pt-BR', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>

                    {/* Avatar User */}
                    {msg.role === 'user' && (
                      <div className="flex-shrink-0 ml-2">
                        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center shadow-sm">
                          <User className="w-4 h-4 text-white" />
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}

              {/* Typing Indicator */}
              {loading && (
                <div className="flex justify-start">
                  <div className="flex-shrink-0 mr-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-sm">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-tl-md shadow-sm">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white border-t border-gray-100">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Digite uma mensagem como cliente..."
                  disabled={loading}
                  className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-50 text-sm"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  className="px-5 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar de Análise - 1 coluna */}
        <div className="space-y-4">

          {/* Card de Sentimento */}
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <ThermometerSun className="w-5 h-5 text-purple-500" />
              <h4 className="font-semibold text-gray-900">Sentimento Detectado</h4>
            </div>
            <div className={`px-4 py-3 rounded-lg ${currentSentiment.bg}`}>
              <p className={`font-medium ${currentSentiment.text}`}>
                {currentSentiment.label}
              </p>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              A IA ajusta o tom da resposta baseado no sentimento do cliente
            </p>
          </Card>

          {/* Card de Qualificação */}
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-5 h-5 text-purple-500" />
              <h4 className="font-semibold text-gray-900">Qualificação</h4>
            </div>
            {lastQualification ? (
              <div className="px-4 py-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-700">{lastQualification}</p>
              </div>
            ) : (
              <p className="text-sm text-gray-400">
                Envie mensagens para ver a qualificação
              </p>
            )}
          </Card>

          {/* Card de Dicas */}
          <Card className="p-4 bg-purple-50 border-purple-200">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-purple-500" />
              <h4 className="font-semibold text-purple-900">Dicas de Teste</h4>
            </div>
            <ul className="text-sm text-purple-800 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-purple-500 mt-0.5">•</span>
                <span>Teste mensagens de frustração para ver a empatia da IA</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-500 mt-0.5">•</span>
                <span>Simule objeções como &quot;tá caro&quot; ou &quot;vou pensar&quot;</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-500 mt-0.5">•</span>
                <span>Pergunte sobre formas de pagamento para ver lead quente</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-500 mt-0.5">•</span>
                <span>Teste perguntas fora do escopo configurado</span>
              </li>
            </ul>
          </Card>

          {/* Info */}
          <Card className="p-4">
            <div className="flex items-start gap-2">
              <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-gray-600">
                  As respostas usam suas configurações atuais (tom, FAQ, escopo, perguntas personalizadas).
                </p>
                <a href="/dashboard/settings" className="text-sm text-blue-600 hover:underline mt-1 inline-block">
                  Ajustar configurações →
                </a>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}