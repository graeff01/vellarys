'use client';

import { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
  X,
  Loader2,
  UserCheck,
  MessageSquare,
  Bell,
  BellOff,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Search,
  Star,
} from 'lucide-react';

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
  active_leads_count?: number; // Opcional: quantos leads o vendedor tem
}

interface AssignSellerModalProps {
  open: boolean;
  leadName?: string | null;
  leadQualification?: string;
  sellers: Seller[];
  loading: boolean;
  onClose: () => void;
  onAssign: (sellerId: number, options: { notes: string; notifySeller: boolean; executeHandoff: boolean }) => void;
}

export function AssignSellerModal({
  open,
  leadName,
  leadQualification,
  sellers,
  loading,
  onClose,
  onAssign,
}: AssignSellerModalProps) {
  const [selectedSellerId, setSelectedSellerId] = useState<number | null>(null);
  const [notes, setNotes] = useState('');
  const [notifySeller, setNotifySeller] = useState(true);
  const [executeHandoff, setExecuteHandoff] = useState(true);
  const [step, setStep] = useState<'select' | 'options'>('select');
  const [mounted, setMounted] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isMobile, setIsMobile] = useState(false);

  const availableSellers = sellers.filter((s) => s.active);
  const isHotLead = leadQualification === 'hot' || leadQualification === 'quente';

  // Detecta mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Monta componente
  useEffect(() => {
    setMounted(true);
  }, []);

  // Bloqueia scroll quando modal aberto
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [open]);

  // ✅ KEYBOARD NAVIGATION
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // ESC fecha modal
      if (e.key === 'Escape') {
        handleClose();
      }
      
      // ENTER avança/confirma
      if (e.key === 'Enter') {
        if (step === 'select' && selectedSellerId) {
          handleNext();
        } else if (step === 'options' && selectedSellerId && !loading) {
          handleConfirm();
        }
      }
      
      // BACKSPACE volta
      if (e.key === 'Backspace' && step === 'options') {
        e.preventDefault();
        setStep('select');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, step, selectedSellerId, loading]);

  // ✅ BUSCA DE VENDEDORES
  const filteredSellers = useMemo(() => {
    if (!searchTerm.trim()) return availableSellers;
    
    const term = searchTerm.toLowerCase();
    return availableSellers.filter(
      (s) =>
        s.name.toLowerCase().includes(term) ||
        s.whatsapp.includes(term)
    );
  }, [availableSellers, searchTerm]);

  // ✅ SUGESTÃO AUTOMÁTICA
  const suggestedSellerId = useMemo(() => {
    if (!filteredSellers.length) return null;
    
    // Prioridade:
    // 1. Disponível (available)
    // 2. Menos leads ativos
    // 3. Primeiro da lista
    
    const available = filteredSellers.filter((s) => s.available);
    
    if (!available.length) {
      return filteredSellers[0]?.id || null;
    }
    
    // Ordena por menos leads
    const sorted = [...available].sort(
      (a, b) => (a.active_leads_count || 0) - (b.active_leads_count || 0)
    );
    
    return sorted[0]?.id || null;
  }, [filteredSellers]);

  // ✅ VIBRAÇÃO TÁTICA (mobile)
  function handleSelectSeller(sellerId: number) {
    // Feedback háptico em mobile
    if (isMobile && 'vibrate' in navigator) {
      navigator.vibrate(10);
    }
    
    setSelectedSellerId(sellerId);
  }

  function handleNext() {
    if (selectedSellerId) {
      // Vibração ao avançar
      if (isMobile && 'vibrate' in navigator) {
        navigator.vibrate(15);
      }
      setStep('options');
    }
  }

  function handleConfirm() {
    if (!selectedSellerId) return;
    
    // Vibração ao confirmar
    if (isMobile && 'vibrate' in navigator) {
      navigator.vibrate([10, 50, 10]);
    }
    
    onAssign(selectedSellerId, {
      notes,
      notifySeller,
      executeHandoff,
    });
  }

  function handleClose() {
    setSelectedSellerId(null);
    setNotes('');
    setNotifySeller(true);
    setExecuteHandoff(true);
    setStep('select');
    setSearchTerm('');
    onClose();
  }

  if (!open || !mounted) return null;

  const selectedSeller = sellers.find((s) => s.id === selectedSellerId);

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* ✅ MOBILE BOTTOM SHEET */}
      <div
        className={`
          relative bg-white w-full max-w-md shadow-2xl z-[10000] overflow-hidden
          ${isMobile
            ? 'fixed bottom-0 left-0 right-0 rounded-t-2xl animate-slideUp max-w-full'
            : 'rounded-xl animate-fadeIn'
          }
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">
              {step === 'select' ? 'Selecionar Vendedor' : 'Opções de Transferência'}
            </h3>
            {leadName && (
              <p className="text-sm text-gray-500 mt-0.5">
                Lead: <span className="font-medium">{leadName}</span>
                {isHotLead && (
                  <span className="ml-2 inline-flex items-center gap-1 text-orange-600">
                    🔥 Quente
                  </span>
                )}
              </p>
            )}
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 hover:bg-gray-200 rounded-lg transition"
            aria-label="Fechar"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className={`p-4 ${isMobile ? 'max-h-[60vh]' : 'max-h-[70vh]'} overflow-y-auto`}>
          {step === 'select' && (
            <>
              {/* ✅ BUSCA */}
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar vendedor..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  autoFocus={!isMobile} // Auto-focus apenas desktop
                />
              </div>

              {/* Instrução */}
              <p className="text-sm text-gray-600 mb-3 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-blue-500" />
                Clique no vendedor que deseja atribuir:
              </p>

              {/* ✅ LOADING STATES */}
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 p-4 rounded-lg border animate-pulse"
                    >
                      <div className="w-10 h-10 bg-gray-200 rounded-full" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-gray-200 rounded w-32" />
                        <div className="h-3 bg-gray-200 rounded w-24" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <>
                  {/* Lista de Vendedores */}
                  <div className="space-y-2">
                    {filteredSellers.map((seller) => {
                      const isSelected = selectedSellerId === seller.id;
                      const isSuggested = seller.id === suggestedSellerId;

                      return (
                        <button
                          key={seller.id}
                          onClick={() => handleSelectSeller(seller.id)}
                          className={`
                            relative w-full flex items-center gap-3 px-4 py-3 rounded-lg border-2 transition-all
                            ${isSelected
                              ? 'border-blue-500 bg-blue-50 shadow-md'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                            }
                          `}
                        >
                          {/* ✅ BADGE SUGERIDO */}
                          {isSuggested && !isSelected && (
                            <div className="absolute -top-2 -right-2 bg-yellow-400 text-yellow-900 text-xs px-2 py-0.5 rounded-full flex items-center gap-1 shadow">
                              <Star className="w-3 h-3" />
                              Sugerido
                            </div>
                          )}

                          <div
                            className={`
                              w-10 h-10 rounded-full flex items-center justify-center
                              ${isSelected
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100'
                              }
                            `}
                          >
                            {isSelected ? (
                              <CheckCircle2 className="w-5 h-5" />
                            ) : (
                              <UserCheck className="w-5 h-5 text-gray-500" />
                            )}
                          </div>

                          <div className="flex-1 text-left">
                            <p
                              className={`font-medium ${
                                isSelected ? 'text-blue-800' : 'text-gray-800'
                              }`}
                            >
                              {seller.name}
                            </p>
                            <p
                              className={`text-sm ${
                                isSelected ? 'text-blue-600' : 'text-gray-500'
                              }`}
                            >
                              {seller.whatsapp}
                              {seller.active_leads_count !== undefined && (
                                <span className="ml-2 text-xs">
                                  • {seller.active_leads_count} leads
                                </span>
                              )}
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            <div
                              className={`w-2.5 h-2.5 rounded-full ${
                                seller.available ? 'bg-green-500' : 'bg-gray-300'
                              }`}
                              title={seller.available ? 'Disponível' : 'Indisponível'}
                            />
                            {isSelected && (
                              <ChevronRight className="w-5 h-5 text-blue-500" />
                            )}
                          </div>
                        </button>
                      );
                    })}

                    {/* Empty state - Busca sem resultados */}
                    {filteredSellers.length === 0 && searchTerm && (
                      <div className="text-center py-8">
                        <Search className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">
                          Nenhum vendedor encontrado para "{searchTerm}"
                        </p>
                        <button
                          onClick={() => setSearchTerm('')}
                          className="text-sm text-blue-600 hover:underline mt-2"
                        >
                          Limpar busca
                        </button>
                      </div>
                    )}

                    {/* Empty state - Sem vendedores */}
                    {availableSellers.length === 0 && (
                      <div className="text-center py-8">
                        <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">Nenhum vendedor disponível.</p>
                        <p className="text-sm text-gray-400 mt-1">
                          Cadastre vendedores na aba Equipe.
                        </p>
                      </div>
                    )}
                  </div>
                </>
              )}
            </>
          )}

          {step === 'options' && selectedSeller && (
            <div className="space-y-4">
              {/* Vendedor Selecionado */}
              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-blue-800">{selectedSeller.name}</p>
                  <p className="text-sm text-blue-600">{selectedSeller.whatsapp}</p>
                </div>
                <button
                  onClick={() => setStep('select')}
                  className="text-sm text-blue-600 hover:underline font-medium"
                >
                  Trocar
                </button>
              </div>

              {/* Opções */}
              <div className="space-y-3">
                {/* Executar Handoff */}
                <label className="flex items-start gap-3 p-3 rounded-lg border cursor-pointer hover:bg-gray-50 transition">
                  <input
                    type="checkbox"
                    checked={executeHandoff}
                    onChange={(e) => setExecuteHandoff(e.target.checked)}
                    className="mt-0.5 w-4 h-4 text-blue-600 rounded"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-500" />
                      <span className="font-medium text-gray-800">Transferir lead</span>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      IA para de atender, vendedor assume o atendimento
                    </p>
                  </div>
                </label>

                {/* Notificar Vendedor */}
                <label className="flex items-start gap-3 p-3 rounded-lg border cursor-pointer hover:bg-gray-50 transition">
                  <input
                    type="checkbox"
                    checked={notifySeller}
                    onChange={(e) => setNotifySeller(e.target.checked)}
                    className="mt-0.5 w-4 h-4 text-blue-600 rounded"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {notifySeller ? (
                        <Bell className="w-4 h-4 text-green-500" />
                      ) : (
                        <BellOff className="w-4 h-4 text-gray-400" />
                      )}
                      <span className="font-medium text-gray-800">
                        Notificar via WhatsApp
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Vendedor recebe mensagem com dados do lead
                    </p>
                  </div>
                </label>
              </div>

              {/* Observações */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  <MessageSquare className="w-4 h-4 inline mr-1.5" />
                  Observações para o vendedor (opcional)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Ex: Cliente com urgência, ligar hoje..."
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={2}
                />
              </div>

              {/* Preview */}
              {notifySeller && (
                <div className="p-3 bg-green-50 border border-green-100 rounded-lg">
                  <div className="flex items-center gap-2 text-green-700 text-sm font-medium mb-1">
                    <CheckCircle2 className="w-4 h-4" />
                    O vendedor receberá via WhatsApp:
                  </div>
                  <ul className="text-sm text-green-600 ml-6 space-y-0.5">
                    <li>• Nome e telefone do lead</li>
                    <li>• Resumo da conversa</li>
                    <li>• Dados coletados pela IA</li>
                    {notes && <li>• Suas observações</li>}
                    <li>• Link direto para WhatsApp do lead</li>
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-4 border-t bg-gray-50">
          <button
            onClick={handleClose}
            className="flex-1 py-2.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition font-medium"
          >
            Cancelar
          </button>

          {step === 'select' && (
            <button
              onClick={handleNext}
              disabled={!selectedSellerId}
              className="flex-1 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              Próximo
              <ChevronRight className="w-4 h-4" />
            </button>
          )}

          {step === 'options' && (
            <button
              onClick={handleConfirm}
              disabled={loading || !selectedSellerId}
              className="flex-1 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <UserCheck className="w-4 h-4" />
                  {executeHandoff ? 'Atribuir e Transferir' : 'Apenas Atribuir'}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Adicionar CSS para animações */}
      <style jsx global>{`
        @keyframes slideUp {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .animate-slideUp {
          animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .animate-fadeIn {
          animation: fadeIn 0.2s ease-out;
        }
      `}</style>
    </div>,
    document.body
  );
}