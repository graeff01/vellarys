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
  title: React.ReactNode;
  subtitle?: string;
  action?: React.ReactNode;
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
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