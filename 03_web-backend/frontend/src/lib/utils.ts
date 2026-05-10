// UTC Date를 KST(+9시간)로 변환
export function toKSTDate(date: Date | string | number): Date {
  const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  // 9시간(32400000ms) 더하기
  return new Date(d.getTime());
}
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
