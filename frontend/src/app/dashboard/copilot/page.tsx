'use client';

import { useState, useRef, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { getToken } from '@/lib/auth';
import {
    Bot, Send, Sparkles, Loader2, User, Trash2, Info
} from 'lucide-react';
import { FeatureGate } from '@/components/FeatureGate';

// Ajuste para pegar a URL da API do ambiente
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ChatMessage {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

export default function CopilotPage() {
    return (
        <FeatureGate feature="copilot_enabled">
            <CopilotContent />
        </FeatureGate>
    );
}

function CopilotContent() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    async function handleSend() {
        if (!input.trim() || loading) return;

        const userMessage: ChatMessage = {
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
            const response = await fetch(`${API_URL}/manager/copilot/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    query: userMessage.content,
                    history: messages.map(m => ({
                        role: m.role,
                        content: m.content,
                    })),
                }),
            });

            if (response.ok) {
                const data = await response.json();
                const assistantMessage: ChatMessage = {
                    id: Date.now(),
                    role: 'assistant',
                    content: data.response,
                    timestamp: new Date(),
                };
                setMessages(prev => [...prev, assistantMessage]);
            } else {
                const error = await response.json();
                setMessages(prev => [...prev, {
                    id: Date.now(),
                    role: 'assistant',
                    content: `❌ Erro: ${error.detail || 'Não foi possível processar a mensagem.'}`,
                    timestamp: new Date(),
                }]);
            }
        } catch (error) {
            console.error('Erro no Vellarys Copilot:', error);
            setMessages(prev => [...prev, {
                id: Date.now(),
                role: 'assistant',
                content: '❌ Erro de conexão. Verifique se o backend está rodando.',
                timestamp: new Date(),
            }]);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="h-[calc(100vh-100px)] sm:h-[calc(100vh-120px)] flex flex-col gap-3 sm:gap-4">
            {/* Header - Mobile Optimized */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 flex-shrink-0">
                <div className="flex-1">
                    <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-2 sm:gap-3">
                        <div className="p-2 sm:p-2.5 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl shadow-lg shadow-indigo-200">
                            <Sparkles className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
                        </div>
                        <span className="hidden sm:inline">Vellarys Copilot</span>
                        <span className="sm:hidden">Copilot</span>
                    </h1>
                    <p className="text-gray-500 mt-1.5 text-xs sm:text-sm">
                        Seu assistente de inteligência. Pergunte sobre leads, vendedores, métricas e configurações da sua empresa.
                    </p>
                </div>

                {messages.length > 0 && (
                    <button
                        onClick={() => setMessages([])}
                        className="flex items-center gap-2 px-3 sm:px-4 py-2 text-xs sm:text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-gray-200 hover:border-red-200"
                    >
                        <Trash2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                        <span className="hidden sm:inline">Limpar Conversa</span>
                        <span className="sm:hidden">Limpar</span>
                    </button>
                )}
            </div>

            {/* Main Chat Card - Mobile Optimized */}
            <Card className="flex-1 flex flex-col shadow-lg border-gray-200 overflow-hidden">

                {/* Messages Area with Internal Scroll */}
                <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-5 bg-gradient-to-b from-slate-50/50 to-white">
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
                            <div className="w-20 h-20 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-2xl flex items-center justify-center shadow-inner">
                                <Sparkles className="w-10 h-10 text-indigo-500" />
                            </div>
                            <div className="text-center space-y-3 max-w-2xl">
                                <p className="font-semibold text-xl text-gray-700">Como posso ajudar hoje?</p>
                                <p className="text-sm text-gray-500 leading-relaxed">
                                    Faça perguntas sobre seus leads, vendedores, métricas de desempenho ou configurações da empresa.
                                </p>
                            </div>

                            {/* Suggestion Pills */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-3xl mt-4">
                                {[
                                    "Quantos leads entraram hoje?",
                                    "Qual vendedor teve melhor performance este mês?",
                                    "Mostre leads quentes da cidade de São Paulo",
                                    "Como estão as conversões desta semana?"
                                ].map((suggestion, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setInput(suggestion)}
                                        className="text-left px-4 py-3 bg-white hover:bg-indigo-50 border border-gray-200 hover:border-indigo-300 rounded-xl text-sm text-gray-700 hover:text-indigo-700 transition-all shadow-sm hover:shadow-md"
                                    >
                                        💡 {suggestion}
                                    </button>
                                ))}
                            </div>

                            {/* Info Banner */}
                            <div className="mt-6 flex items-start gap-3 p-4 bg-blue-50 border border-blue-100 rounded-xl max-w-2xl">
                                <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                                <div className="text-sm text-blue-800">
                                    <p className="font-semibold mb-1">Escopo do Copilot</p>
                                    <p className="text-blue-700">
                                        Este assistente responde apenas sobre dados da <strong>sua empresa</strong>. Ele não tem acesso a informações externas ou de outros clientes.
                                    </p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <>
                            {messages.map((msg) => (
                                <div key={msg.id} className={`flex ${msg.role === 'assistant' ? 'justify-start' : 'justify-end'} animate-in fade-in slide-in-from-bottom-2`}>

                                    {msg.role === 'assistant' && (
                                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center flex-shrink-0 mr-3 shadow-md">
                                            <Sparkles className="w-5 h-5 text-white" />
                                        </div>
                                    )}

                                    <div
                                        className={`max-w-[75%] px-5 py-4 rounded-2xl shadow-sm ${msg.role === 'assistant'
                                            ? 'bg-white text-gray-800 border border-gray-100 rounded-tl-sm'
                                            : 'bg-indigo-600 text-white rounded-tr-sm'
                                            }`}
                                    >
                                        <div className="prose prose-sm max-w-none">
                                            <p className="whitespace-pre-wrap leading-relaxed m-0">{msg.content}</p>
                                        </div>
                                        <span className={`text-[10px] mt-2 block ${msg.role === 'assistant' ? 'text-gray-400' : 'text-indigo-200'}`}>
                                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>

                                    {msg.role === 'user' && (
                                        <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 ml-3">
                                            <User className="w-5 h-5 text-slate-600" />
                                        </div>
                                    )}
                                </div>
                            ))}

                            {loading && (
                                <div className="flex justify-start animate-in fade-in slide-in-from-left-2">
                                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center flex-shrink-0 mr-3 shadow-md">
                                        <Sparkles className="w-5 h-5 text-white" />
                                    </div>
                                    <div className="bg-white border border-gray-100 px-5 py-4 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-2">
                                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </>
                    )}
                </div>

                {/* Input Area - Fixed at Bottom - Mobile Optimized */}
                <div className="p-3 sm:p-5 bg-white border-t border-gray-200 flex-shrink-0">
                    <div className="flex items-center gap-2 sm:gap-3">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                            placeholder="Digite sua pergunta..."
                            disabled={loading}
                            className="flex-1 px-3 sm:px-5 py-2.5 sm:py-3.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white focus:border-transparent transition-all text-xs sm:text-sm placeholder:text-gray-400 disabled:opacity-50"
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || loading}
                            className="p-2.5 sm:p-3.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg flex-shrink-0"
                        >
                            {loading ? <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" /> : <Send className="w-4 h-4 sm:w-5 sm:h-5" />}
                        </button>
                    </div>
                    <p className="text-center text-[10px] sm:text-xs text-gray-400 mt-2 sm:mt-3">
                        O Copilot analisa dados em tempo real da sua empresa. Respostas podem levar alguns segundos.
                    </p>
                </div>
            </Card>
        </div>
    );
}
