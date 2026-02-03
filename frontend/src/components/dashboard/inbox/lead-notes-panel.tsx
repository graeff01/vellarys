/**
 * LeadNotesPanel - Painel de Anotações Internas
 * ==============================================
 *
 * Sidebar deslizante para visualizar e criar anotações internas sobre o lead.
 * Anotações não são visíveis para o cliente, apenas para a equipe.
 */

'use client';

import { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { StickyNote, Trash2, Plus } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import axios from 'axios';
import { cn } from '@/lib/utils';
import { getToken } from '@/lib/auth';

interface LeadNote {
  id: number;
  lead_id: number;
  author_id: number;
  author_name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

interface LeadNotesPanelProps {
  leadId: number;
  children?: React.ReactNode;
}

export function LeadNotesPanel({ leadId, children }: LeadNotesPanelProps) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState<LeadNote[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Carrega notas quando abre o painel
  useEffect(() => {
    if (open) {
      loadNotes();
    }
  }, [open, leadId]);

  const loadNotes = async () => {
    setIsLoading(true);
    try {
      const token = getToken();
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/seller/inbox/leads/${leadId}/notes`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setNotes(response.data);
    } catch (error) {
      console.error('Erro ao carregar notas:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createNote = async () => {
    if (!newNoteContent.trim()) return;

    setIsCreating(true);
    try {
      const token = getToken();
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/seller/inbox/leads/${leadId}/notes`,
        { content: newNoteContent },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Limpa input
      setNewNoteContent('');

      // Recarrega notas
      await loadNotes();
    } catch (error) {
      console.error('Erro ao criar nota:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const deleteNote = async (noteId: number) => {
    if (!confirm('Tem certeza que deseja excluir esta anotação?')) {
      return;
    }

    try {
      const token = getToken();
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/seller/inbox/leads/${leadId}/notes/${noteId}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Recarrega notas
      await loadNotes();
    } catch (error) {
      console.error('Erro ao excluir nota:', error);
      alert('Erro ao excluir nota. Apenas o autor pode excluir suas próprias notas.');
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        {children || (
          <Button variant="outline" size="sm">
            <StickyNote className="h-4 w-4 mr-2" />
            Anotações
            {notes.length > 0 && (
              <span className="ml-2 px-1.5 py-0.5 text-xs bg-primary text-primary-foreground rounded-full">
                {notes.length}
              </span>
            )}
          </Button>
        )}
      </SheetTrigger>

      <SheetContent className="w-[90%] sm:max-w-md bg-white border-l-2 border-gray-200">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <StickyNote className="h-5 w-5" />
            Anotações Internas
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {/* Criar nova nota */}
          <div className="space-y-2">
            <Textarea
              placeholder="Adicionar anotação privada sobre o lead..."
              value={newNoteContent}
              onChange={(e) => setNewNoteContent(e.target.value)}
              rows={3}
              className="resize-none"
            />
            <Button
              onClick={createNote}
              disabled={!newNoteContent.trim() || isCreating}
              size="sm"
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              {isCreating ? 'Salvando...' : 'Adicionar Anotação'}
            </Button>
          </div>

          {/* Lista de notas */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium mb-3">
              Histórico ({notes.length})
            </h3>

            <ScrollArea className="h-[calc(100vh-320px)]">
              {isLoading ? (
                <div className="p-8 text-center text-muted-foreground">
                  Carregando anotações...
                </div>
              ) : notes.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <StickyNote className="h-12 w-12 mx-auto mb-2 opacity-20" />
                  <p>Nenhuma anotação ainda</p>
                  <p className="text-xs mt-1">
                    Adicione informações privadas sobre este lead
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {notes.map((note) => (
                    <div
                      key={note.id}
                      className={cn(
                        "p-3 rounded-lg border-l-4",
                        "bg-yellow-50 border-yellow-400",
                        "shadow-sm"
                      )}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-muted-foreground">
                            {note.author_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(note.created_at), {
                              addSuffix: true,
                              locale: ptBR
                            })}
                          </p>
                        </div>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteNote(note.id)}
                          className="h-6 w-6 p-0"
                        >
                          <Trash2 className="h-3 w-3 text-destructive" />
                        </Button>
                      </div>

                      <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
