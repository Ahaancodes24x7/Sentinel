import { clsx } from 'clsx';
import type { ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge conditional class names, then resolve Tailwind conflicts.
 * The single sanctioned way to build a className in this codebase — never
 * concatenate template literals (they leak the ternary's indentation
 * whitespace straight into the class attribute).
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export type { ClassValue };
