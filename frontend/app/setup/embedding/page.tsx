'use client';

import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useEffect, useState } from 'react';
import axios from 'axios';

interface EmbeddingStatus {
  status: string;
  dependencies: string[];
  progress_percent: number;
}

export default function EmbeddingSetup() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus | null>(null);
  const [selectedDeps, setSelectedDeps] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingEmbedding, setStartingEmbedding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }

    if (status === 'authenticated') {
      initializePage();
    }
  }, [status, router]);

  useEffect(() => {
    if (embeddingStatus?.status === 'in_progress') {
      const interval = setInterval(pollStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [embeddingStatus]);

  const initializePage = async () => {
    try {
      const statusResponse = await axios.get('http://localhost:8000/api/v1/setup/status', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });

      if (statusResponse.data.selected_dependencies) {
        setSelectedDeps(statusResponse.data.selected_dependencies);
      }

      await pollStatus();
      setLoading(false);
    } catch (err) {
      console.error('Failed to initialize embedding page:', err);
      setLoading(false);
    }
  };

  const pollStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/embedding/status', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      setEmbeddingStatus(response.data);
    } catch (err) {
      console.error('Failed to poll status:', err);
    }
  };

  const startEmbedding = async () => {
    if (!selectedDeps.length) {
      setError('No dependencies selected');
      return;
    }

    setStartingEmbedding(true);
    try {
      await axios.post(
        'http://localhost:8000/api/v1/embedding/start',
        { dependency_names: selectedDeps },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      // Start polling
      await pollStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start embedding');
      setStartingEmbedding(false);
    }
  };

  const handleComplete = async () => {
    try {
      await axios.post('http://localhost:8000/api/v1/embedding/complete-phase2', {}, {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      router.push('/setup/github-connection');
    } catch (err) {
      console.error('Failed to complete Phase 2:', err);
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  const isEmbeddingStarted = embeddingStatus?.status === 'in_progress' || embeddingStatus?.status === 'completed';
  const isComplete = embeddingStatus?.status === 'completed';

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Phase 2: Embedding & Vector DB
            </h1>
            <p className="text-gray-600">
              Converting documentation into AI embeddings for semantic search
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {/* Selected Dependencies */}
          <div className="mb-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="font-semibold text-gray-900 mb-2">Selected Dependencies:</h3>
            <p className="text-gray-700">{selectedDeps.join(', ')}</p>
          </div>

          {!isEmbeddingStarted ? (
            <div>
              <p className="text-gray-600 mb-6">
                Click the button below to start embedding. This process will:
              </p>
              <ul className="list-disc list-inside text-gray-600 mb-8 space-y-2">
                <li>Split documentation into chunks</li>
                <li>Generate embeddings using Ollama AI</li>
                <li>Index vectors in the database</li>
                <li>Prepare for semantic search queries</li>
              </ul>

              <button
                onClick={startEmbedding}
                disabled={startingEmbedding}
                className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition"
              >
                {startingEmbedding ? 'Starting...' : 'Start Embedding Process'}
              </button>
            </div>
          ) : (
            <div>
              {/* Progress Bar */}
              <div className="mb-8">
                <div className="flex justify-between items-center mb-2">
                  <p className="text-sm font-semibold text-gray-700">Progress</p>
                  <p className="text-sm text-gray-600">{embeddingStatus?.progress_percent || 0}%</p>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className={`h-4 rounded-full transition-all duration-300 ${
                      isComplete ? 'bg-green-600' : 'bg-blue-600'
                    }`}
                    style={{
                      width: `${embeddingStatus?.progress_percent || 0}%`,
                    }}
                  ></div>
                </div>
              </div>

              {/* Status Message */}
              <div className="mb-8 p-4 bg-gray-50 rounded-lg">
                {isComplete ? (
                  <div className="text-center">
                    <p className="text-lg font-semibold text-green-600 mb-2">
                      ✓ Embedding Complete!
                    </p>
                    <p className="text-gray-600">
                      {selectedDeps.length} dependency(ies) embedded and indexed
                    </p>
                  </div>
                ) : (
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3"></div>
                    <p className="text-gray-700 font-semibold">
                      Embedding in progress...
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      This may take a few minutes
                    </p>
                  </div>
                )}
              </div>

              {/* Details */}
              <div className="p-4 bg-gray-50 rounded-lg mb-8">
                <p className="text-sm font-semibold text-gray-700 mb-2">Status: {embeddingStatus?.status}</p>
                {embeddingStatus?.dependencies && (
                  <div className="space-y-1">
                    {embeddingStatus.dependencies.map((dep: string) => (
                      <p key={dep} className="text-sm text-gray-600">
                        • {dep}
                      </p>
                    ))}
                  </div>
                )}
              </div>

              {/* Navigation Buttons */}
              <div className="flex gap-4">
                {isComplete && (
                  <button
                    onClick={handleComplete}
                    className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition"
                  >
                    Continue to Phase 3: GitHub Connection
                  </button>
                )}
                <button
                  onClick={() => router.push('/dashboard')}
                  className={`${
                    isComplete ? 'flex-1' : 'w-full'
                  } px-6 py-3 bg-gray-400 hover:bg-gray-500 text-white font-semibold rounded-lg transition`}
                >
                  Skip to Dashboard
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

