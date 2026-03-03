'use client';

import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useEffect } from 'react';

export default function EmbeddingSetup() {
  const router = useRouter();
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }
  }, [status, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Phase 2: Embedding & Vector DB
            </h1>
            <p className="text-gray-600 mb-8">
              Converting documentation into AI embeddings for semantic search...
            </p>

            <div className="inline-block">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
            </div>

            <div className="mt-8 p-6 bg-blue-50 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-3">What's happening:</h3>
              <ul className="text-left text-gray-700 space-y-2 max-w-md mx-auto">
                <li>✓ Loading documentation chunks</li>
                <li>⏳ Converting to embeddings (using Ollama)</li>
                <li>⏳ Indexing in vector database</li>
                <li>⏳ Preparing for RAG queries</li>
              </ul>
            </div>

            <p className="mt-8 text-sm text-gray-600">
              This typically takes 2-5 minutes depending on the amount of documentation.
            </p>

            <button
              onClick={() => router.push('/dashboard')}
              className="mt-8 px-6 py-2 bg-gray-400 hover:bg-gray-500 text-white font-semibold rounded-lg transition"
            >
              Skip to Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
