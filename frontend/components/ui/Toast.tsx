"use client";
import React, { useEffect } from "react";

export interface ToastProps {
  message: string;
  type?: "success" | "error" | "warning" | "info";
  duration?: number;
  onClose: () => void;
}

export default function Toast({
  message,
  type = "info",
  duration = 3000,
  onClose,
}: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const variants = {
    success: "bg-green-600",
    error: "bg-red-600",
    warning: "bg-yellow-500 text-black",
    info: "bg-blue-600",
  };

  return (
    <div
      className={`fixed top-5 right-5 px-5 py-3 rounded-lg shadow-lg text-white z-50 ${variants[type]}`}
    >
      {message}
    </div>
  );
}