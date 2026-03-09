import type { Metadata } from 'next';
import { AuthProvider } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'DEPFIX — CI/CD Error Analysis',
  description: 'AI-powered CI/CD error analysis and auto-fix generation using RAG and local LLMs',
};

// Prevent static prerendering since app uses dynamic auth and session data
export const dynamic = 'force-dynamic';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
