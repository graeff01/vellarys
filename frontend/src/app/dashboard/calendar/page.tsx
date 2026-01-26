'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  Plus, ChevronLeft, ChevronRight, Calendar as CalendarIcon,
  Clock, MapPin, Phone, User, CheckCircle2, XCircle, Loader2
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, addMonths, subMonths } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface Appointment {
  id: number;
  title: string;
  description?: string;
  appointment_type: string;
  scheduled_at: string;
  duration_minutes: number;
  location?: string;
  status: string;
  lead_name: string;
  lead_phone?: string;
  seller_name: string;
}

const STATUS_COLORS = {
  scheduled: 'bg-blue-100 text-blue-700',
  confirmed: 'bg-green-100 text-green-700',
  completed: 'bg-gray-100 text-gray-700',
  cancelled: 'bg-red-100 text-red-700',
  no_show: 'bg-orange-100 text-orange-700',
};

const STATUS_LABELS = {
  scheduled: 'Agendado',
  confirmed: 'Confirmado',
  completed: 'Completo',
  cancelled: 'Cancelado',
  no_show: 'Não compareceu',
};

const TYPE_LABELS = {
  visit: 'Visita',
  call: 'Ligação',
  meeting: 'Reunião',
  demo: 'Demonstração',
  videocall: 'Videochamada',
};

export default function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadAppointments();
  }, [currentMonth]);

  async function loadAppointments() {
    try {
      setLoading(true);
      const month = currentMonth.getMonth() + 1;
      const year = currentMonth.getFullYear();

      const response = await fetch(
        `/api/v1/appointments/calendar?month=${month}&year=${year}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Erro ao carregar agendamentos');
      }

      const data = await response.json();

      // Converter objeto agrupado por dia em array flat
      const allAppointments: Appointment[] = [];
      Object.keys(data).forEach(date => {
        allAppointments.push(...data[date]);
      });

      setAppointments(allAppointments);
    } catch (err) {
      console.error('Erro ao carregar agendamentos:', err);
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar agendamentos',
        description: 'Tente novamente mais tarde'
      });
    } finally {
      setLoading(false);
    }
  }

  function getAppointmentsForDay(day: Date) {
    return appointments.filter(appt => {
      const apptDate = new Date(appt.scheduled_at);
      return isSameDay(apptDate, day);
    });
  }

  function previousMonth() {
    setCurrentMonth(subMonths(currentMonth, 1));
  }

  function nextMonth() {
    setCurrentMonth(addMonths(currentMonth, 1));
  }

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

  // Preencher dias anteriores para alinhar ao início da semana
  const startDay = monthStart.getDay();
  const previousDays = startDay === 0 ? 6 : startDay - 1;

  const calendarDays: Date[] = [];
  for (let i = previousDays; i > 0; i--) {
    const day = new Date(monthStart);
    day.setDate(day.getDate() - i);
    calendarDays.push(day);
  }
  calendarDays.push(...daysInMonth);

  const selectedDayAppointments = selectedDay ? getAppointmentsForDay(selectedDay) : [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Calendário de Agendamentos</h1>
          <p className="text-gray-500 mt-1">Gerencie suas visitas e compromissos</p>
        </div>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Novo Agendamento
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar */}
        <Card className="lg:col-span-2 p-6">
          {/* Month Navigation */}
          <div className="flex items-center justify-between mb-6">
            <Button variant="outline" size="sm" onClick={previousMonth}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <h2 className="text-xl font-semibold capitalize">
              {format(currentMonth, 'MMMM yyyy', { locale: ptBR })}
            </h2>
            <Button variant="outline" size="sm" onClick={nextMonth}>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-2">
            {/* Weekday Headers */}
            {['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'].map(day => (
              <div key={day} className="text-center text-sm font-semibold text-gray-600 py-2">
                {day}
              </div>
            ))}

            {/* Calendar Days */}
            {calendarDays.map((day, idx) => {
              const dayAppointments = getAppointmentsForDay(day);
              const isCurrentMonth = isSameMonth(day, currentMonth);
              const isSelected = selectedDay && isSameDay(day, selectedDay);
              const isToday = isSameDay(day, new Date());

              return (
                <button
                  key={idx}
                  onClick={() => setSelectedDay(day)}
                  className={`
                    min-h-[80px] p-2 border rounded-lg text-left transition
                    ${isCurrentMonth ? 'bg-white' : 'bg-gray-50 text-gray-400'}
                    ${isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}
                    ${isToday ? 'border-blue-300 font-semibold' : ''}
                    hover:border-blue-400
                  `}
                >
                  <div className="text-sm mb-1">{format(day, 'd')}</div>
                  {dayAppointments.length > 0 && (
                    <div className="space-y-1">
                      {dayAppointments.slice(0, 2).map(appt => (
                        <div
                          key={appt.id}
                          className={`text-xs px-1 py-0.5 rounded truncate ${STATUS_COLORS[appt.status as keyof typeof STATUS_COLORS]}`}
                        >
                          {format(new Date(appt.scheduled_at), 'HH:mm')} {appt.title}
                        </div>
                      ))}
                      {dayAppointments.length > 2 && (
                        <div className="text-xs text-gray-500">
                          +{dayAppointments.length - 2} mais
                        </div>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {loading && (
            <div className="flex items-center justify-center mt-6">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          )}
        </Card>

        {/* Sidebar - Day Details */}
        <Card className="p-6">
          {selectedDay ? (
            <>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <CalendarIcon className="w-5 h-5" />
                {format(selectedDay, "d 'de' MMMM", { locale: ptBR })}
              </h3>

              {selectedDayAppointments.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <CalendarIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                  <p>Nenhum agendamento</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {selectedDayAppointments.map(appt => (
                    <Card key={appt.id} className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold">{appt.title}</h4>
                        <Badge className={STATUS_COLORS[appt.status as keyof typeof STATUS_COLORS]}>
                          {STATUS_LABELS[appt.status as keyof typeof STATUS_LABELS]}
                        </Badge>
                      </div>

                      <div className="space-y-2 text-sm text-gray-600">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          {format(new Date(appt.scheduled_at), 'HH:mm')} ({appt.duration_minutes}min)
                        </div>

                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4" />
                          {appt.lead_name}
                        </div>

                        {appt.lead_phone && (
                          <div className="flex items-center gap-2">
                            <Phone className="w-4 h-4" />
                            {appt.lead_phone}
                          </div>
                        )}

                        {appt.location && (
                          <div className="flex items-center gap-2">
                            <MapPin className="w-4 h-4" />
                            {appt.location}
                          </div>
                        )}
                      </div>

                      <div className="mt-3 pt-3 border-t text-xs text-gray-500">
                        {TYPE_LABELS[appt.appointment_type as keyof typeof TYPE_LABELS]} • {appt.seller_name}
                      </div>

                      <div className="mt-3 flex gap-2">
                        <Button size="sm" variant="outline" className="flex-1 gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Completar
                        </Button>
                        <Button size="sm" variant="outline" className="flex-1 gap-1">
                          <XCircle className="w-3 h-3" />
                          Cancelar
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="text-center text-gray-500 py-8">
              <CalendarIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>Selecione um dia no calendário</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
