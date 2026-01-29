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

      <PopoverContent className="w-96 p-0 bg-white border-gray-300 shadow-lg" align="start">
        {/* Header com busca */}
        <div className="p-3 border-b bg-white">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-white"
            />
          </div>
        </div>

        {/* Filtro de categorias */}
        {categories.length > 0 && (
          <div className="p-2 border-b bg-gray-50 flex gap-1 flex-wrap">
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
        <ScrollArea className="h-[300px] bg-white">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
              Carregando templates...
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="font-medium">{searchQuery ? 'Nenhum template encontrado' : 'Nenhum template disponível'}</p>
              <p className="text-xs text-gray-400 mt-1">
                {!searchQuery && 'Crie seu primeiro template para começar'}
              </p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {filteredTemplates.map(template => (
                <button
                  key={template.id}
                  onClick={() => handleSelectTemplate(template)}
                  className={cn(
                    "w-full text-left p-3 rounded-md hover:bg-blue-50 transition-colors bg-white",
                    "focus:outline-none focus:ring-2 focus:ring-blue-500 border border-transparent hover:border-blue-200"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-gray-900">{template.name}</span>
                        {template.shortcut && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs bg-gray-100 text-gray-700 rounded">
                            <Zap className="h-3 w-3" />
                            {template.shortcut}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                        {template.content}
                      </p>
                    </div>

                    {template.usage_count > 0 && (
                      <span className="text-xs text-gray-500 whitespace-nowrap">
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
        <div className="p-2 border-t bg-gray-50 text-xs text-gray-600 text-center">
          Dica: Digite <kbd className="px-1 py-0.5 bg-gray-200 text-gray-700 rounded font-mono">/</kbd> no campo de mensagem para atalhos
        </div>
      </PopoverContent>
    </Popover>
  );
}
