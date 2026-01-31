/**
 * MessageSearch - Busca de Mensagens
 * ===================================
 *
 * Modal full-screen para busca full-text em mensagens.
 * Navega para o lead ao clicar em um resultado.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, MessageSquare, User } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import axios from 'axios';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';

interface SearchResult {
  message_id: number;
  content: string;
  role: string;
  created_at: string;
  lead: {
    id: number;
    name: string;
    phone: string;
  };
}

interface MessageSearchProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MessageSearch({ open, onOpenChange }: MessageSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce da query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Busca quando query muda
  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setResults([]);
      return;
    }

    searchMessages(debouncedQuery);
  }, [debouncedQuery]);

  const searchMessages = async (searchQuery: string) => {
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/seller/inbox/search?q=${encodeURIComponent(searchQuery)}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setResults(response.data.results || []);
    } catch (error) {
      console.error('Erro na busca:', error);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Navega para lead
  const handleSelectResult = (result: SearchResult) => {
    // Fecha modal
    onOpenChange(false);

    // Navega para página do inbox com lead selecionado
    router.push(`/dashboard/inbox?lead=${result.lead.id}`);

    // Limpa busca
    setQuery('');
    setResults([]);
  };

  // Destaca texto buscado
  const highlightText = (text: string, highlight: string): React.ReactNode => {
    if (!highlight.trim()) {
      return text;
    }

    const regex = new RegExp(`(${highlight})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-200 text-foreground rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] p-0">
        <DialogHeader className="p-6 pb-3">
          <DialogTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Buscar Mensagens
          </DialogTitle>
        </DialogHeader>

        {/* Campo de busca */}
        <div className="px-6 pb-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Digite para buscar em todas as conversas..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9"
              autoFocus
            />
          </div>
        </div>

        {/* Resultados */}
        <ScrollArea className="flex-1 px-6 pb-6">
          {query.length < 2 ? (
            <div className="py-12 text-center text-muted-foreground">
              <Search className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p>Digite pelo menos 2 caracteres para buscar</p>
            </div>
          ) : isLoading ? (
            <div className="py-12 text-center text-muted-foreground">
              Buscando...
            </div>
          ) : results.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p>Nenhuma mensagem encontrada</p>
              <p className="text-sm mt-1">Tente usar outras palavras-chave</p>
            </div>
          ) : (
            <div className="space-y-2">
              {results.map((result) => (
                <button
                  key={result.message_id}
                  onClick={() => handleSelectResult(result)}
                  className={cn(
                    "w-full text-left p-4 rounded-lg border hover:bg-accent transition-colors",
                    "focus:outline-none focus:ring-2 focus:ring-ring"
                  )}
                >
                  {/* Lead info */}
                  <div className="flex items-center gap-2 mb-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium text-sm">{result.lead.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {result.lead.phone}
                    </span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(result.created_at), {
                        addSuffix: true,
                        locale: ptBR
                      })}
                    </span>
                  </div>

                  {/* Message content com highlight */}
                  <div className={cn(
                    "text-sm p-2 rounded",
                    result.role === 'user' ? 'bg-muted' : 'bg-primary/10'
                  )}>
                    <span className="text-xs font-medium text-muted-foreground mr-2">
                      {result.role === 'user' ? 'Lead' : 'Você'}:
                    </span>
                    <span>{highlightText(result.content, query)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Footer com dica */}
        <div className="p-4 border-t text-xs text-muted-foreground text-center">
          Dica: Use <kbd className="px-1.5 py-0.5 bg-muted rounded">Ctrl+K</kbd> para abrir a busca
        </div>
      </DialogContent>
    </Dialog>
  );
}
