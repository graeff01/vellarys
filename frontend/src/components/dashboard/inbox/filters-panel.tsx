/**
 * FiltersPanel - Painel de Filtros Avançados
 * ===========================================
 *
 * Painel lateral/dropdown com filtros avançados para leads.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { SlidersHorizontal, X, Calendar as CalendarIcon, Flame, Snowflake, Wind } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { cn } from '@/lib/utils';

export interface InboxFilters {
  attendedBy: 'all' | 'ai' | 'seller';
  status?: 'open' | 'in_progress' | 'converted' | 'lost';
  qualification?: 'hot' | 'warm' | 'cold';
  dateFrom?: Date;
  dateTo?: Date;
}

interface FiltersPanelProps {
  filters: InboxFilters;
  onFiltersChange: (filters: InboxFilters) => void;
  leadsCount?: number;
}

export function FiltersPanel({ filters, onFiltersChange, leadsCount }: FiltersPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  const hasActiveFilters =
    filters.attendedBy !== 'all' ||
    filters.status ||
    filters.qualification ||
    filters.dateFrom ||
    filters.dateTo;

  const activeFiltersCount = [
    filters.attendedBy !== 'all',
    !!filters.status,
    !!filters.qualification,
    !!(filters.dateFrom || filters.dateTo),
  ].filter(Boolean).length;

  function handleReset() {
    onFiltersChange({
      attendedBy: 'all',
      status: undefined,
      qualification: undefined,
      dateFrom: undefined,
      dateTo: undefined,
    });
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="relative gap-2 h-8 text-xs">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filtros
          {activeFiltersCount > 0 && (
            <span className="absolute -top-1.5 -right-1.5 h-4 w-4 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
              {activeFiltersCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        className="w-[90vw] max-w-md p-4"
        align="start"
        side="bottom"
        sideOffset={8}
        collisionPadding={16}
      >
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between border-b pb-2">
            <h4 className="font-semibold text-sm text-gray-900">Filtros Avançados</h4>
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleReset}
                className="h-6 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <X className="h-3 w-3 mr-1" />
                Limpar
              </Button>
            )}
          </div>

          {/* Atendido Por */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold text-gray-700">
              Atendido Por
            </Label>
            <RadioGroup
              value={filters.attendedBy}
              onValueChange={(value: any) =>
                onFiltersChange({ ...filters, attendedBy: value })
              }
              className="space-y-1.5"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="all" id="all" />
                <Label htmlFor="all" className="cursor-pointer text-sm">
                  Todos
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="ai" id="ai" />
                <Label htmlFor="ai" className="cursor-pointer text-sm">
                  IA (Automático)
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="seller" id="seller" />
                <Label htmlFor="seller" className="cursor-pointer text-sm">
                  Vendedor (Manual)
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Status */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold text-gray-700">
              Status
            </Label>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { value: undefined, label: 'Todos' },
                { value: 'open', label: 'Aberto' },
                { value: 'in_progress', label: 'Em Progresso' },
                { value: 'converted', label: 'Convertido' },
                { value: 'lost', label: 'Perdido' },
              ].map((option) => (
                <Button
                  key={option.value || 'all'}
                  variant={filters.status === option.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() =>
                    onFiltersChange({ ...filters, status: option.value as any })
                  }
                  className="text-xs"
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Qualificação */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold text-gray-700">
              Qualificação
            </Label>
            <div className="grid grid-cols-4 gap-1.5">
              {[
                { value: undefined, label: 'Todos', icon: null },
                { value: 'hot', label: 'Quente', icon: Flame, color: 'text-red-500' },
                { value: 'warm', label: 'Morno', icon: Wind, color: 'text-orange-500' },
                { value: 'cold', label: 'Frio', icon: Snowflake, color: 'text-blue-500' },
              ].map((option) => (
                <Button
                  key={option.value || 'all'}
                  variant={filters.qualification === option.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() =>
                    onFiltersChange({ ...filters, qualification: option.value as any })
                  }
                  className={cn(
                    "text-xs flex-col h-auto py-2 gap-1",
                    filters.qualification === option.value && option.color
                  )}
                >
                  {option.icon && <option.icon className="h-3 w-3" />}
                  {option.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Data */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold text-gray-700">
              Período
            </Label>
            <div className="grid grid-cols-2 gap-1.5">
              {/* De */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="text-xs justify-start">
                    <CalendarIcon className="h-3 w-3 mr-1" />
                    {filters.dateFrom ? format(filters.dateFrom, 'dd/MM', { locale: ptBR }) : 'De'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start" side="bottom">
                  <Calendar
                    mode="single"
                    selected={filters.dateFrom}
                    onSelect={(date) =>
                      onFiltersChange({ ...filters, dateFrom: date })
                    }
                    locale={ptBR}
                  />
                </PopoverContent>
              </Popover>

              {/* Até */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="text-xs justify-start">
                    <CalendarIcon className="h-3 w-3 mr-1" />
                    {filters.dateTo ? format(filters.dateTo, 'dd/MM', { locale: ptBR }) : 'Até'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start" side="bottom">
                  <Calendar
                    mode="single"
                    selected={filters.dateTo}
                    onSelect={(date) =>
                      onFiltersChange({ ...filters, dateTo: date })
                    }
                    locale={ptBR}
                    disabled={(date) =>
                      filters.dateFrom ? date < filters.dateFrom : false
                    }
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          {/* Results count */}
          {leadsCount !== undefined && (
            <div className="pt-2 border-t text-center">
              <p className="text-xs text-muted-foreground">
                {leadsCount} {leadsCount === 1 ? 'lead encontrado' : 'leads encontrados'}
              </p>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
