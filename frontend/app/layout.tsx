import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'RAG CI/CD Analysis',
  description: 'AI-powered CI/CD error analysis and auto-fix generation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
