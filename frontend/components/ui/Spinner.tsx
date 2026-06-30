import React from "react";

export interface SpinnerProps {
  size?: number;
  className?: string;
}

export default function Spinner({
  size = 24,
  className = "",
}: SpinnerProps) {
  return (
    <div
      className={`animate-spin rounded-full border-4 border-gray-300 border-t-blue-600 ${className}`}
      style={{
        width: size,
        height: size,
      }}
    />
  );
}