/**
 * ActionsMenu - Menu de Ações da Conversa
 * ========================================
 *
 * Dropdown com ações disponíveis para o lead atual.
 */

'use client';

import { Archive, UserX, RefreshCw, MoreVertical, FileText, AlertCircle } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

interface ActionsMenuProps {
  leadId: number;
  leadName: string;
  attendedBy: string;
  onArchive: () => void;
  onReturnToAI?: () => void;
  onViewNotes?: () => void;
  onReportIssue?: () => void;
}

export function ActionsMenu({
  leadId,
  leadName,
  attendedBy,
  onArchive,
  onReturnToAI,
  onViewNotes,
  onReportIssue,
}: ActionsMenuProps) {
  const isSellerAttending = attendedBy === 'seller';

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <MoreVertical className="h-4 w-4" />
          <span className="sr-only">Abrir menu de ações</span>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>Ações do Lead</DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Ver Notas */}
        {onViewNotes && (
          <DropdownMenuItem onClick={onViewNotes}>
            <FileText className="mr-2 h-4 w-4" />
            Ver Anotações
          </DropdownMenuItem>
        )}

        {/* Devolver para IA */}
        {isSellerAttending && onReturnToAI && (
          <DropdownMenuItem onClick={onReturnToAI}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Devolver para IA
          </DropdownMenuItem>
        )}

        <DropdownMenuSeparator />

        {/* Arquivar */}
        <DropdownMenuItem onClick={onArchive} className="text-orange-600 focus:text-orange-600">
          <Archive className="mr-2 h-4 w-4" />
          Arquivar Lead
        </DropdownMenuItem>

        {/* Reportar Problema */}
        {onReportIssue && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onReportIssue} className="text-red-600 focus:text-red-600">
              <AlertCircle className="mr-2 h-4 w-4" />
              Reportar Problema
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
