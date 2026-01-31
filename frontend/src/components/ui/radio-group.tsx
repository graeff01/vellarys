'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface RadioGroupProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function RadioGroup({ value, onValueChange, children, className }: RadioGroupProps) {
  return (
    <div className={cn('grid gap-2', className)} role="radiogroup">
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, {
            ...child.props,
            checked: child.props.value === value,
            onCheckedChange: () => onValueChange(child.props.value),
          } as any);
        }
        return child;
      })}
    </div>
  );
}

interface RadioGroupItemProps {
  value: string;
  id: string;
  checked?: boolean;
  onCheckedChange?: () => void;
  className?: string;
}

export function RadioGroupItem({ value, id, checked, onCheckedChange, className }: RadioGroupItemProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={checked}
      onClick={onCheckedChange}
      className={cn(
        'aspect-square h-4 w-4 rounded-full border border-gray-300 text-gray-900 ring-offset-white focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-950 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        checked && 'border-blue-600 bg-blue-600',
        className
      )}
    >
      {checked && (
        <div className="flex items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-white" />
        </div>
      )}
    </button>
  );
}
