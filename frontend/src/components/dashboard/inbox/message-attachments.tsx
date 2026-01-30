/**
 * MessageAttachments - Renderiza anexos de mensagens
 * ==================================================
 *
 * Suporta: imagens, PDFs, documentos, áudios, vídeos
 */

'use client';

import { FileText, File, Music, Video, Download, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Attachment {
  type: 'image' | 'document' | 'audio' | 'video' | 'file';
  url: string;
  filename?: string;
  size?: number;
  mime_type?: string;
}

interface MessageAttachmentsProps {
  attachments: Attachment[];
  className?: string;
}

export function MessageAttachments({ attachments, className }: MessageAttachmentsProps) {
  if (!attachments || attachments.length === 0) return null;

  return (
    <div className={cn("space-y-2 mt-2", className)}>
      {attachments.map((attachment, index) => (
        <AttachmentItem key={index} attachment={attachment} />
      ))}
    </div>
  );
}

function AttachmentItem({ attachment }: { attachment: Attachment }) {
  const { type, url, filename, size } = attachment;

  // Imagens: mostrar preview
  if (type === 'image') {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="block rounded-lg overflow-hidden max-w-xs hover:opacity-90 transition-opacity"
      >
        <img
          src={url}
          alt={filename || 'Imagem'}
          className="w-full h-auto"
          loading="lazy"
        />
      </a>
    );
  }

  // Áudios: player nativo
  if (type === 'audio') {
    return (
      <div className="bg-gray-100 rounded-lg p-2 max-w-xs">
        <audio controls className="w-full">
          <source src={url} type={attachment.mime_type || 'audio/mpeg'} />
          Seu navegador não suporta áudio.
        </audio>
        {filename && (
          <p className="text-xs text-gray-600 mt-1">{filename}</p>
        )}
      </div>
    );
  }

  // Vídeos: player nativo
  if (type === 'video') {
    return (
      <div className="rounded-lg overflow-hidden max-w-md">
        <video controls className="w-full">
          <source src={url} type={attachment.mime_type || 'video/mp4'} />
          Seu navegador não suporta vídeo.
        </video>
        {filename && (
          <p className="text-xs text-gray-600 mt-1">{filename}</p>
        )}
      </div>
    );
  }

  // Documentos/Arquivos: card com ícone e download
  const icon = type === 'document' ? FileText : File;
  const Icon = icon;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 p-3 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors max-w-xs group"
    >
      <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
        <Icon className="w-5 h-5 text-blue-600" />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {filename || 'Arquivo'}
        </p>
        {size && (
          <p className="text-xs text-gray-500">
            {formatFileSize(size)}
          </p>
        )}
      </div>

      <Download className="w-4 h-4 text-gray-400 group-hover:text-gray-600 flex-shrink-0" />
    </a>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
