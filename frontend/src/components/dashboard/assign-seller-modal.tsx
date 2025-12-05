'use client';

import React from 'react';
import { X, UserPlus, Loader2 } from 'lucide-react';

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
  sellers: Seller[];
  loading?: boolean;
  onClose: () => void;
  onAssign: (sellerId: number) => Promise<void>;
}

export function AssignSellerModal({
  open,
  leadName,
  sellers,
  loading,
  onClose,
  onAssign,
}: AssignSellerModalProps) {
  if (!open) return null;

  const availableSellers = sellers.filter((s) => s.active);

  async function handleClick(sellerId: number) {
    await onAssign(sellerId);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* overlay */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />

      {/* modal */}
      <div className="relative z-50 w-full max-w-md rounded-2xl bg-white shadow-2xl border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <p className="text-xs uppercase tracking-wide text-blue-500 font-semibold">
              Atribuir vendedor
            </p>
            <h2 className="text-base font-semibold text-gray-900">
              {leadName || 'Lead sem nome'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-gray-500">
            Selecione abaixo quem vai receber esse lead. Só serão exibidos
            vendedores ativos neste tenant.
          </p>

          {availableSellers.length === 0 ? (
            <div className="rounded-lg bg-gray-50 border border-dashed border-gray-200 p-4 text-sm text-gray-500">
              Nenhum vendedor cadastrado ou ativo.
              <br />
              <span className="text-xs text-gray-400">
                Cadastre vendedores na aba “Vendedores” do menu lateral.
              </span>
            </div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {availableSellers.map((seller) => (
                <button
                  key={seller.id}
                  disabled={loading}
                  onClick={() => handleClick(seller.id)}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50/60 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                      <UserPlus className="w-4 h-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {seller.name}
                      </p>
                      <p className="text-xs text-gray-500">{seller.whatsapp}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex h-1.5 w-1.5 rounded-full ${
                        seller.available ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    />
                    <span className="text-xs text-gray-400">
                      {seller.available ? 'Disponível' : 'Ocupado'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
          <span className="text-[11px] text-gray-400">
            Essa ação será registrada no histórico do lead.
          </span>
          {loading && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Salvando...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
