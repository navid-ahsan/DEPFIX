'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import axios from 'axios';

interface Dependency {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  documentation_url: string;
  repository_url: string;
}

export default function DependenciesSetup() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
      return;
    }

    if (status === 'authenticated') {
      fetchDependencies();
    }
  }, [status, router]);

  const fetchDependencies = async () => {
    try {
      const response = await axios.get(
        'http://localhost:8000/api/v1/setup/dependencies'
      );
      setDependencies(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load dependencies');
      setLoading(false);
      console.error(err);
    }
  };

  const toggleDependency = (name: string) => {
    setSelected((prev) =>
      prev.includes(name)
        ? prev.filter((d) => d !== name)
        : [...prev, name]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (selected.length === 0) {
      setError('Please select at least one dependency');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(
        'http://localhost:8000/api/v1/setup/select',
        { dependency_names: selected },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      // Redirect to progress page
      router.push('/setup/progress');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to select dependencies');
      setSubmitting(false);
      console.error(err);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Step 1: Select Dependencies
            </h1>
            <p className="text-gray-600">
              Choose the Python packages you want to analyze. We'll download their documentation to help resolve CI/CD errors.
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {/* Dependencies Grid */}
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              {dependencies.map((dep) => (
                <label
                  key={dep.id}
                  className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                    selected.includes(dep.name)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selected.includes(dep.name)}
                      onChange={() => toggleDependency(dep.name)}
                      className="mt-1 w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">
                        {dep.display_name}
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {dep.description}
                      </p>
                      <div className="flex gap-2 mt-2">
                        <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                          {dep.category}
                        </span>
                        {dep.documentation_url && (
                          <a
                            href={dep.documentation_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-block px-2 py-1 bg-gray-100 text-blue-600 text-xs rounded hover:bg-gray-200"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Docs
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {/* Selection Summary */}
            {selected.length > 0 && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-blue-900 font-semibold">
                  Selected {selected.length} {selected.length === 1 ? 'dependency' : 'dependencies'}:
                </p>
                <p className="text-blue-800 mt-1">
                  {selected.join(', ')}
                </p>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex gap-4 justify-between">
              <button
                type="button"
                onClick={() => router.push('/dashboard')}
                className="px-6 py-2 bg-gray-400 hover:bg-gray-500 text-white font-semibold rounded-lg transition"
              >
                Skip for Now
              </button>
              <button
                type="submit"
                disabled={submitting || selected.length === 0}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition"
              >
                {submitting ? 'Loading docs...' : 'Continue to Phase 2'}
              </button>
            </div>
          </form>

          {/* Info Section */}
          <div className="mt-8 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold text-gray-900 mb-2">What happens next?</h3>
            <ul className="text-sm text-gray-700 space-y-1">
              <li>✓ We'll download documentation for selected packages</li>
              <li>✓ Convert docs into embeddings using AI</li>
              <li>✓ Index them in a vector database</li>
              <li>✓ Ready for RAG queries on CI/CD errors</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
