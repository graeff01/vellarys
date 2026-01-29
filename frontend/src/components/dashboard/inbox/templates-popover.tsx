/**
 * TemplatesPopover - Seletor de Templates de Resposta
 * ====================================================
 *
 * Popover que lista templates disponíveis com busca e categorias.
 * Ao selecionar um template, interpola variáveis e insere no input.
 */

'use client';

import { useState, useEffect } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageSquare, Search, Zap } from 'lucide-react';
import { useTemplates, ResponseTemplate } from '@/hooks/use-templates';
import { cn } from '@/lib/utils';

interface TemplatesPopoverProps {
  leadId: number;
  onSelectTemplate: (content: string) => void;
  children?: React.ReactNode;
}

export function TemplatesPopover({ leadId, onSelectTemplate, children }: TemplatesPopoverProps) {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const { templates, isLoading, useTemplate } = useTemplates({ autoLoad: true });

  // Filtra templates localmente
  const filteredTemplates = templates.filter(template => {
    const matchesSearch =
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (template.shortcut && template.shortcut.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesCategory = selectedCategory ? template.category === selectedCategory : true;

    return matchesSearch && matchesCategory;
  });

  // Extrai categorias únicas e capitaliza
  const categories = Array.from(new Set(templates.map(t => t.category).filter(Boolean)));

  // Capitaliza categoria
  const capitalizeCategory = (cat: string) => {
    if (!cat) return '';
    return cat.charAt(0).toUpperCase() + cat.slice(1);
  };

  // Seleciona template
  const handleSelectTemplate = async (template: ResponseTemplate) => {
    try {
      // Interpola variáveis via backend
      const interpolated = await useTemplate(template.id, leadId);

      // Callback com conteúdo interpolado
      onSelectTemplate(interpolated);

      // Fecha popover
      setOpen(false);

      // Limpa busca
      setSearchQuery('');
    } catch (error) {
      console.error('Erro ao usar template:', error);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        {children || (
          <Button variant="outline" size="sm">
            <MessageSquare className="h-4 w-4 mr-2" />
            Templates
          </Button>
        )}
      </PopoverTrigger>

      <PopoverContent className="w-96 p-0" align="start">
        {/* Header com busca */}
        <div className="p-3 border-b">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {/* Filtro de categorias */}
        {categories.length > 0 && (
          <div className="p-2 border-b flex gap-1 flex-wrap">
            <Button
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              Todos
            </Button>
            {categories.map(category => (
              <Button
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {capitalizeCategory(category as string)}
              </Button>
            ))}
          </div>
        )}

        {/* Lista de templates */}
        <ScrollArea className="h-[300px]">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground">
              Carregando templates...
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              {searchQuery ? 'Nenhum template encontrado' : 'Nenhum template disponível'}
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {filteredTemplates.map(template => (
                <button
                  key={template.id}
                  onClick={() => handleSelectTemplate(template)}
                  className={cn(
                    "w-full text-left p-3 rounded-md hover:bg-accent transition-colors",
                    "focus:outline-none focus:ring-2 focus:ring-ring"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{template.name}</span>
                        {template.shortcut && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs bg-muted rounded">
                            <Zap className="h-3 w-3" />
                            {template.shortcut}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {template.content}
                      </p>
                    </div>

                    {template.usage_count > 0 && (
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {template.usage_count}x
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Footer com dica */}
        <div className="p-2 border-t text-xs text-muted-foreground text-center">
          Dica: Digite <kbd className="px-1 py-0.5 bg-muted rounded">/</kbd> no campo de mensagem
        </div>
      </PopoverContent>
    </Popover>
  );
}
