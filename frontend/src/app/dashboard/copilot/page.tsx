'use client';

import { useState, useRef, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { getToken } from '@/lib/auth';
import {
    Bot, Send, Sparkles, Loader2, User,
    MessageSquare, Trash2
} from 'lucide-react';

// Ajuste para pegar a URL da API do ambiente
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ChatMessage {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

export default function CopilotPage() {
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
            console.error('Erro no Jarvis:', error);
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
        <div className="space-y-6 max-w-5xl mx-auto h-[calc(100vh-100px)] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between flex-shrink-0">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl shadow-lg shadow-indigo-200">
                            <Bot className="w-8 h-8 text-white" />
                        </div>
                        Jarvis Copilot
                    </h1>
                    <p className="text-gray-500 mt-1">
                        Seu analista de dados pessoal. Pergunte sobre métricas, leads e insights.
                    </p>
                </div>

                {messages.length > 0 && (
                    <button
                        onClick={() => setMessages([])}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                        <Trash2 className="w-4 h-4" />
                        Limpar Conversa
                    </button>
                )}
            </div>

            {/* Chat Container */}
            <Card className="flex-1 flex flex-col shadow-xl border-indigo-50 overflow-hidden">

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-6">
                            <div className="w-24 h-24 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-full flex items-center justify-center animate-pulse">
                                <Sparkles className="w-12 h-12 text-indigo-400" />
                            </div>
                            <div className="text-center space-y-2">
                                <p className="font-semibold text-lg text-gray-600">Como posso ajudar hoje, Gestor?</p>
                                <div className="flex flex-col gap-2 text-sm text-gray-500">
                                    <p>"Quantos leads entraram hoje?"</p>
                                    <p>"Qual vendedor teve melhor performance este mês?"</p>
                                    <p>"Mostre leads quentes interessados em aluguel"</p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        messages.map((msg) => (
                            <div key={msg.id} className={`flex ${msg.role === 'assistant' ? 'justify-start' : 'justify-end'}`}>

                                {msg.role === 'assistant' && (
                                    <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0 mr-3 mt-1 shadow-md">
                                        <Bot className="w-5 h-5 text-white" />
                                    </div>
                                )}

                                <div
                                    className={`max-w-[85%] px-5 py-4 rounded-2xl shadow-sm ${msg.role === 'assistant'
                                        ? 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                                        : 'bg-indigo-600 text-white rounded-tr-none'
                                        }`}
                                >
                                    <div className="prose prose-sm max-w-none dark:prose-invert">
                                        <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                                    </div>
                                    <span className={`text-[10px] mt-2 block opacity-70 ${msg.role === 'assistant' ? 'text-gray-400' : 'text-indigo-200'}`}>
                                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>

                                {msg.role === 'user' && (
                                    <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 ml-3 mt-1">
                                        <User className="w-5 h-5 text-slate-500" />
                                    </div>
                                )}
                            </div>
                        ))
                    )}

                    {loading && (
                        <div className="flex justify-start animate-in fade-in slide-in-from-left-2">
                            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0 mr-3 mt-1">
                                <Bot className="w-5 h-5 text-white" />
                            </div>
                            <div className="bg-white border border-gray-100 px-5 py-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white border-t border-gray-100">
                    <div className="relative flex items-center">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Pergunte ao Jarvis sobre seus dados..."
                            disabled={loading}
                            className="w-full pl-5 pr-14 py-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all shadow-inner text-base"
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || loading}
                            className="absolute right-2 p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors shadow-md"
                        >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                        </button>
                    </div>
                    <p className="text-center text-xs text-gray-400 mt-2">
                        O Jarvis analisa dados em tempo real. Respostas podem levar alguns segundos.
                    </p>
                </div>
            </Card>
        </div>
    );
}
