/**
 * ArchiveModal - Modal de Arquivamento de Leads
 * ==============================================
 *
 * Modal para arquivar um ou múltiplos leads com motivo opcional.
 */

'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Archive, Loader2, AlertTriangle } from 'lucide-react';
import axios from 'axios';

interface ArchiveModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leadIds: number[];
  leadNames?: string[];
  onSuccess: () => void;
}

export function ArchiveModal({ open, onOpenChange, leadIds, leadNames, onSuccess }: ArchiveModalProps) {
  const [reason, setReason] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const isBulk = leadIds.length > 1;

  async function handleArchive() {
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');

      // Arquiva cada lead
      await Promise.all(
        leadIds.map(leadId =>
          axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/seller/inbox/leads/${leadId}/archive`,
            { reason: reason || null },
            {
              headers: { Authorization: `Bearer ${token}` }
            }
          )
        )
      );

      onSuccess();
      onOpenChange(false);
      setReason('');
    } catch (error: any) {
      console.error('Erro ao arquivar:', error);
      alert(error.response?.data?.detail || 'Erro ao arquivar lead(s)');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Archive className="h-5 w-5 text-orange-500" />
            {isBulk ? `Arquivar ${leadIds.length} Leads` : 'Arquivar Lead'}
          </DialogTitle>
          <DialogDescription>
            {isBulk
              ? 'Os leads arquivados não aparecerão mais na lista principal, mas podem ser recuperados depois.'
              : 'Este lead não aparecerá mais na lista principal, mas pode ser recuperado depois.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Preview dos leads */}
          {leadNames && leadNames.length > 0 && (
            <div className="p-3 bg-orange-50 border border-orange-100 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-orange-800">
                  <p className="font-medium mb-1">
                    {isBulk ? 'Leads que serão arquivados:' : 'Lead que será arquivado:'}
                  </p>
                  <ul className="space-y-0.5">
                    {leadNames.slice(0, 5).map((name, i) => (
                      <li key={i}>• {name}</li>
                    ))}
                    {leadNames.length > 5 && (
                      <li className="text-orange-600 font-medium">
                        + {leadNames.length - 5} outros
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Motivo (opcional) */}
          <div className="space-y-2">
            <Label htmlFor="reason">
              Motivo (opcional)
            </Label>
            <Textarea
              id="reason"
              placeholder="Ex: Sem interesse, não respondeu, fora do perfil..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="resize-none"
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              Este motivo será salvo para referência futura
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleArchive}
            disabled={isLoading}
            className="bg-orange-600 hover:bg-orange-700"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Arquivando...
              </>
            ) : (
              <>
                <Archive className="mr-2 h-4 w-4" />
                {isBulk ? `Arquivar ${leadIds.length}` : 'Arquivar'}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
