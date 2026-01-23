'use client';

/**
 * LEAD WIDGET RENDERER
 * ====================
 *
 * Renderiza widgets dinamicamente baseado no tipo.
 * Conecta o registry com os componentes reais.
 */

import { Card } from '@/components/ui/card';
import {
  ContactWidget,
  SellerWidget,
  InsightsWidget,
  OpportunitiesWidget,
  TimelineWidget,
  NotesWidget,
  ChatWidget,
} from './lead-widgets';
import { Opportunity } from '@/lib/api';

// =============================================
// TIPOS
// =============================================

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  email: string | null;
  city: string | null;
  qualification: string;
  status: string;
  summary: string | null;
  custom_data: Record<string, any>;
  created_at: string;
  assigned_seller?: {
    id: number;
    name: string;
    whatsapp: string;
  } | null;
}

interface LeadEvent {
  id: number;
  event_type: string;
  old_value: string | null;
  new_value: string | null;
  description: string;
  created_at: string;
}

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
}

interface Message {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

interface WidgetConfig {
  i: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  maxW?: number;
  minH?: number;
  maxH?: number;
}

interface LeadWidgetRendererProps {
  config: WidgetConfig;
  lead: Lead;
  messages: Message[];
  events: LeadEvent[];
  sellers: Seller[];
  opportunities: Opportunity[];
  products?: { id: number; name: string }[];
  onAssignSeller: (sellerId: number) => void;
  onRemoveSeller: () => void;
  onAddNote: (content: string) => void;
  onDeleteNote: (noteId: number) => void;
  onReloadOpportunities: () => void;
  assigningSeller: boolean;
  chatScrollRef?: React.RefObject<HTMLDivElement>;
}

// =============================================
// WIDGET RENDERER
// =============================================

export function LeadWidgetRenderer({
  config,
  lead,
  messages,
  events,
  sellers,
  opportunities,
  products,
  onAssignSeller,
  onRemoveSeller,
  onAddNote,
  onDeleteNote,
  onReloadOpportunities,
  assigningSeller,
  chatScrollRef,
}: LeadWidgetRendererProps) {
  const renderWidget = () => {
    switch (config.type) {
      case 'lead_contact':
        return <ContactWidget lead={lead} />;

      case 'lead_seller':
        return (
          <SellerWidget
            lead={lead}
            sellers={sellers}
            onAssignSeller={onAssignSeller}
            onRemoveSeller={onRemoveSeller}
            assigning={assigningSeller}
          />
        );

      case 'lead_insights':
        return <InsightsWidget lead={lead} />;

      case 'lead_opportunities':
        return (
          <OpportunitiesWidget
            leadId={lead.id}
            opportunities={opportunities}
            onReload={onReloadOpportunities}
            products={products}
          />
        );

      case 'lead_timeline':
        return <TimelineWidget events={events} />;

      case 'lead_notes':
        return (
          <NotesWidget
            lead={lead}
            onAddNote={onAddNote}
            onDeleteNote={onDeleteNote}
          />
        );

      case 'lead_chat':
        return <ChatWidget messages={messages} scrollRef={chatScrollRef} />;

      default:
        return (
          <Card className="bg-slate-50 border-slate-200 rounded-2xl p-4 h-full flex items-center justify-center">
            <p className="text-sm text-slate-400">Widget não encontrado: {config.type}</p>
          </Card>
        );
    }
  };

  return (
    <div className="h-full w-full overflow-hidden">
      {renderWidget()}
    </div>
  );
}

export default LeadWidgetRenderer;
