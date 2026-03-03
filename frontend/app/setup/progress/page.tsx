'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import axios from 'axios';

interface DependencyProgress {
  name: string;
  status: 'loading' | 'completed' | 'failed';
  chunks_loaded: number;
  total_chunks?: number;
}

export default function SetupProgress() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [setupStatus, setSetupStatus] = useState<any>(null);
  const [depProgress, setDepProgress] = useState<DependencyProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [docsLoaded, setDocsLoaded] = useState<Record<string, any>>({});
  const [allComplete, setAllComplete] = useState(false);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
      return;
    }

    if (status === 'authenticated') {
      fetchSetupStatus();
      const interval = setInterval(fetchSetupStatus, 2000); // Poll every 2 seconds
      return () => clearInterval(interval);
    }
  }, [status, router]);

  const fetchSetupStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/setup/status', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });

      setSetupStatus(response.data);

      // Load docs for each selected dependency
      if (response.data.selected_dependencies) {
        loadDependencyDocs(response.data.selected_dependencies);
      }

      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch setup status:', err);
      setLoading(false);
    }
  };

  const loadDependencyDocs = async (depNames: string[]) => {
    const newProgress: DependencyProgress[] = [];
    const newDocsLoaded: Record<string, any> = {};

    for (const depName of depNames) {
      try {
        // Add to progress
        newProgress.push({
          name: depName,
          status: 'loading',
          chunks_loaded: 0,
        });

        // Fetch doc data
        const response = await axios.get(
          `http://localhost:8000/api/v1/setup/docs/${depName}`,
          {
            headers: {
              Authorization: `Bearer ${session?.accessToken}`,
            },
          }
        );

        newDocsLoaded[depName] = response.data;

        // Update progress
        setDepProgress((prev) => {
          const updated = prev.filter((p) => p.name !== depName);
          updated.push({
            name: depName,
            status: 'completed',
            chunks_loaded: response.data.total_chunks,
            total_chunks: response.data.total_chunks,
          });
          return updated;
        });
      } catch (err) {
        console.error(`Failed to load docs for ${depName}:`, err);
        setDepProgress((prev) => {
          const updated = prev.filter((p) => p.name !== depName);
          updated.push({
            name: depName,
            status: 'failed',
            chunks_loaded: 0,
          });
          return updated;
        });
      }
    }

    setDepProgress(newProgress);
    setDocsLoaded(newDocsLoaded);
  };

  const handleComplete = async () => {
    try {
      await axios.post('http://localhost:8000/api/v1/setup/complete-phase1', {}, {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      router.push('/setup/embedding'); // Go to Phase 2
    } catch (err) {
      console.error('Failed to complete Phase 1:', err);
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading setup status...</p>
        </div>
      </div>
    );
  }

  const allDocsLoaded = setupStatus?.selected_dependencies?.every(
    (dep: string) => docsLoaded[dep]
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Phase 1: Loading Documentation
            </h1>
            <p className="text-gray-600">
              We're downloading and preparing documentation for the selected dependencies.
            </p>
          </div>

          {/* Progress Tracking */}
          <div className="space-y-4 mb-8">
            {setupStatus?.selected_dependencies?.map((depName: string) => {
              const doc = docsLoaded[depName];
              const isComplete = !!doc;

              return (
                <div key={depName} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-4">
                    {isComplete ? (
                      <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center text-white">
                        ✓
                      </div>
                    ) : (
                      <div className="w-6 h-6 bg-blue-500 rounded-full animate-spin"></div>
                    )}
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">{depName}</h3>
                      {isComplete && (
                        <p className="text-sm text-gray-600">
                          {doc.total_chunks} chunks loaded, ready for embedding
                        </p>
                      )}
                      {!isComplete && (
                        <p className="text-sm text-gray-600">Loading...</p>
                      )}
                    </div>
                  </div>

                  {/* Sample Chunks Preview */}
                  {isComplete && doc.sample_chunks && (
                    <div className="mt-3 pl-10 border-l-2 border-blue-200">
                      <p className="text-xs font-semibold text-gray-700 mb-2">
                        Sample content:
                      </p>
                      <div className="space-y-1">
                        {doc.sample_chunks.slice(0, 2).map((chunk: any, idx: number) => (
                          <p key={idx} className="text-xs text-gray-600 line-clamp-2">
                            {chunk.text?.substring(0, 100)}...
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Overall Progress Bar */}
          {setupStatus?.selected_dependencies && (
            <div className="mb-8">
              <div className="flex justify-between items-center mb-2">
                <p className="text-sm font-semibold text-gray-700">Overall Progress</p>
                <p className="text-sm text-gray-600">
                  {Object.keys(docsLoaded).length} / {setupStatus.selected_dependencies.length}
                </p>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                  style={{
                    width: `${(Object.keys(docsLoaded).length / setupStatus.selected_dependencies.length) * 100}%`,
                  }}
                ></div>
              </div>
            </div>
          )}

          {/* Next Steps */}
          {allDocsLoaded && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg mb-6">
              <h3 className="font-semibold text-green-900 mb-2">✓ All documentation loaded!</h3>
              <p className="text-sm text-green-800 mb-4">
                Next: We'll embed these documents and index them in the vector database.
              </p>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex gap-4">
            {allDocsLoaded && (
              <button
                onClick={handleComplete}
                className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition"
              >
                Continue to Phase 2: Embedding
              </button>
            )}
            <button
              onClick={() => router.push('/dashboard')}
              className="px-6 py-3 bg-gray-400 hover:bg-gray-500 text-white font-semibold rounded-lg transition"
            >
              Skip to Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
