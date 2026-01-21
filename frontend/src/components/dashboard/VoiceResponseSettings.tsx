'use client';

import { useState } from 'react';
import { Mic, Volume2, Play, Pause, CheckCircle2 } from 'lucide-react';

interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: string;
  recommended: boolean;
  preview_text?: string;
}

interface VoiceResponseSettings {
  enabled: boolean;
  voice: string;
  speed: number;
  always_audio: boolean;
  max_chars_for_audio: number;
  persona_name: string;
}

interface VoiceResponseSettingsProps {
  settings: VoiceResponseSettings;
  voiceOptions: VoiceOption[];
  onChange: (settings: VoiceResponseSettings) => void;
}

export default function VoiceResponseSettingsCard({
  settings,
  voiceOptions,
  onChange,
}: VoiceResponseSettingsProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  const updateSetting = <K extends keyof VoiceResponseSettings>(
    key: K,
    value: VoiceResponseSettings[K]
  ) => {
    onChange({ ...settings, [key]: value });
  };

  const selectedVoice = voiceOptions.find((v) => v.id === settings.voice) || voiceOptions[0];

  // Preview de voz real usando TTS
  const playVoicePreview = async (voiceId: string) => {
    // Se já está tocando esta voz, para
    if (playingVoice === voiceId && audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
      setIsPlaying(false);
      setPlayingVoice(null);
      return;
    }

    // Para qualquer áudio que esteja tocando
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }

    try {
      setIsPlaying(true);
      setPlayingVoice(voiceId);

      // Chama API para gerar preview
      const response = await fetch(`/api/v1/settings/voice-preview/${voiceId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Erro ao gerar preview');
      }

      const data = await response.json();

      // Converte base64 para blob
      const audioBlob = await fetch(
        `data:${data.mime_type};base64,${data.audio_base64}`
      ).then((res) => res.blob());

      // Cria URL do blob
      const audioUrl = URL.createObjectURL(audioBlob);

      // Cria elemento de áudio
      const audio = new Audio(audioUrl);
      setAudioElement(audio);

      // Quando terminar de tocar
      audio.onended = () => {
        setIsPlaying(false);
        setPlayingVoice(null);
        URL.revokeObjectURL(audioUrl);
      };

      // Se der erro
      audio.onerror = () => {
        setIsPlaying(false);
        setPlayingVoice(null);
        URL.revokeObjectURL(audioUrl);
        console.error('Erro ao tocar áudio');
      };

      // Toca o áudio
      await audio.play();
    } catch (error) {
      console.error('Erro ao gerar preview de voz:', error);
      setIsPlaying(false);
      setPlayingVoice(null);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header com Toggle Principal */}
      <div className="p-6 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
              <Mic className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Voice-First</h3>
              <p className="text-sm text-gray-500">
                Responda com áudio quando o cliente enviar áudio
              </p>
            </div>
          </div>

          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(e) => updateSetting('enabled', e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-14 h-7 bg-gray-200 peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-purple-600 shadow-inner"></div>
          </label>
        </div>

        {settings.enabled && (
          <div className="mt-4 p-3 bg-white/60 rounded-lg border border-purple-100">
            <p className="text-sm text-purple-700">
              <span className="font-bold">Como funciona:</span> Quando o cliente enviar um
              áudio, a IA transcreve, processa e responde com um áudio natural.
            </p>
          </div>
        )}
      </div>

      {/* Configurações (só aparecem se habilitado) */}
      {settings.enabled && (
        <div className="p-6 space-y-6">
          {/* Seleção de Voz */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-3">
              Escolha a Voz da IA
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {voiceOptions.map((voice) => (
                <button
                  key={voice.id}
                  onClick={() => updateSetting('voice', voice.id)}
                  className={`relative p-4 rounded-xl border-2 text-left transition-all ${
                    settings.voice === voice.id
                      ? 'border-purple-500 bg-purple-50 shadow-md'
                      : 'border-gray-200 hover:border-purple-300 bg-white'
                  }`}
                >
                  {voice.recommended && (
                    <span className="absolute -top-2 -right-2 bg-green-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                      Recomendado
                    </span>
                  )}

                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-gray-900">{voice.name}</span>
                    {settings.voice === voice.id && (
                      <CheckCircle2 className="w-5 h-5 text-purple-600" />
                    )}
                  </div>

                  <p className="text-xs text-gray-500 mb-3">{voice.description}</p>

                  {/* Botão de Preview */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      playVoicePreview(voice.id);
                    }}
                    className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all ${
                      playingVoice === voice.id
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {playingVoice === voice.id ? (
                      <>
                        <Pause className="w-3 h-3" /> Tocando...
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3" /> Ouvir
                      </>
                    )}
                  </button>
                </button>
              ))}
            </div>
          </div>

          {/* Nome da Persona */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">
              Nome da Assistente (opcional)
            </label>
            <input
              type="text"
              value={settings.persona_name}
              onChange={(e) => updateSetting('persona_name', e.target.value)}
              placeholder="Ex: Ana, Julia, Assistente..."
              className="w-full max-w-xs px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
            <p className="mt-1 text-xs text-gray-400">
              A IA pode se apresentar com esse nome nas respostas
            </p>
          </div>

          {/* Velocidade da Fala */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">
              Velocidade da Fala
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0.75"
                max="1.5"
                step="0.05"
                value={settings.speed}
                onChange={(e) => updateSetting('speed', parseFloat(e.target.value))}
                className="w-48 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
              />
              <span className="text-sm font-mono bg-gray-100 px-3 py-1 rounded">
                {settings.speed.toFixed(2)}x
              </span>
            </div>
            <div className="flex justify-between text-xs text-gray-400 w-48 mt-1">
              <span>Mais lento</span>
              <span>Normal</span>
              <span>Rápido</span>
            </div>
          </div>

          {/* Configurações Avançadas */}
          <div className="pt-4 border-t border-gray-100 space-y-4">
            <h4 className="text-sm font-bold text-gray-700">Comportamento</h4>

            {/* Always Audio Toggle */}
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium text-gray-900">Sempre responder com áudio</p>
                <p className="text-xs text-gray-500">
                  Se desativado, só responde áudio quando recebe áudio
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.always_audio}
                  onChange={(e) => updateSetting('always_audio', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
              </label>
            </div>

            {/* Max Chars */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Limite de caracteres para áudio
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={settings.max_chars_for_audio}
                  onChange={(e) =>
                    updateSetting('max_chars_for_audio', parseInt(e.target.value) || 500)
                  }
                  min={100}
                  max={2000}
                  className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <span className="text-sm text-gray-500">caracteres</span>
              </div>
              <p className="mt-1 text-xs text-gray-400">
                Respostas maiores que isso serão enviadas como texto
              </p>
            </div>
          </div>

          {/* Info Box */}
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
            <div className="flex items-start gap-3">
              <Volume2 className="w-5 h-5 text-blue-600 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-blue-900">Custo estimado</p>
                <p className="text-xs text-blue-700 mt-1">
                  ~R$0,02 por resposta de áudio (20 segundos). O áudio é gerado pela OpenAI TTS
                  com qualidade profissional.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
