import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ally AI",
  description: "Receptionist-led healthcare intake and chat flow",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
