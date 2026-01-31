interface CardProps {
  children: React.ReactNode;
  className?: string;
  overflow?: boolean;
}

export function Card({ children, className = '', overflow = false }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow p-6 ${overflow ? 'overflow-visible' : ''} ${className}`}>
      {children}
    </div>
  );
}

interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return <div className={`text-gray-700 ${className}`}>{children}</div>;
}

interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export function CardFooter({ children, className = '' }: CardFooterProps) {
  return <div className={`mt-6 pt-4 border-t border-gray-200 flex items-center justify-end gap-3 ${className}`}>{children}</div>;
}

interface CardHeaderProps {
  title?: React.ReactNode;
  subtitle?: string;
  action?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export function CardHeader({ title, subtitle, action, children, className = '' }: CardHeaderProps) {
  // Se tiver children, usa a API nova do shadcn/ui
  if (children) {
    return <div className={`flex flex-col space-y-1.5 p-6 ${className}`}>{children}</div>;
  }

  // Senão, usa a API antiga (backward compatible)
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
}

export function CardTitle({ children, className = '' }: CardTitleProps) {
  return <h3 className={`text-2xl font-semibold leading-none tracking-tight ${className}`}>{children}</h3>;
}