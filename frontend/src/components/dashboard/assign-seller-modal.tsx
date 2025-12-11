'use client';

import { useState } from 'react';
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
} from 'lucide-react';

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
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

  const availableSellers = sellers.filter((s) => s.active);
  const isHotLead = leadQualification === 'hot' || leadQualification === 'quente';

  function handleSelectSeller(sellerId: number) {
    setSelectedSellerId(sellerId);
    setStep('options');
  }

  function handleConfirm() {
    if (!selectedSellerId) return;
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
    onClose();
  }

  if (!open) return null;

  const selectedSeller = sellers.find((s) => s.id === selectedSellerId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white w-full max-w-md rounded-xl shadow-2xl z-50 animate-fadeIn overflow-hidden">
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
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          {step === 'select' && (
            <>
              {/* Lista de Vendedores */}
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {availableSellers.map((seller) => (
                  <button
                    key={seller.id}
                    onClick={() => handleSelectSeller(seller.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-lg border hover:bg-blue-50 hover:border-blue-200 transition group"
                  >
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center group-hover:bg-blue-100">
                      <UserCheck className="w-5 h-5 text-gray-500 group-hover:text-blue-600" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="font-medium text-gray-800">{seller.name}</p>
                      <p className="text-sm text-gray-500">{seller.whatsapp}</p>
                    </div>
                    <div
                      className={`w-2.5 h-2.5 rounded-full ${
                        seller.available ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                      title={seller.available ? 'Disponível' : 'Indisponível'}
                    />
                  </button>
                ))}

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

          {step === 'options' && selectedSeller && (
            <div className="space-y-4">
              {/* Vendedor Selecionado */}
              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <UserCheck className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-blue-800">{selectedSeller.name}</p>
                  <p className="text-sm text-blue-600">{selectedSeller.whatsapp}</p>
                </div>
                <button
                  onClick={() => setStep('select')}
                  className="text-sm text-blue-600 hover:underline"
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
                      <span className="font-medium text-gray-800">Notificar via WhatsApp</span>
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
                    <li>• Qualificação e resumo da conversa</li>
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
    </div>
  );
}