import React from "react";

export interface ModalProps {
  isOpen: boolean;
  title?: string;
  children: React.ReactNode;
  onClose: () => void;
}

export default function Modal({
  isOpen,
  title,
  children,
  onClose,
}: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-md p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-500 hover:text-black text-xl"
        >
          ×
        </button>

        {title && (
          <h2 className="text-xl font-semibold mb-4">
            {title}
          </h2>
        )}

        <div>{children}</div>
      </div>
    </div>
  );
}