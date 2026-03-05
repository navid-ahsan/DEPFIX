'use client';

import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useState, useEffect } from 'react';
import axios from 'axios';

export default function GitHubConnection() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [gistUrl, setGistUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }

    if (status === 'authenticated') {
      checkConnectionStatus();
    }
  }, [status, router]);

  const checkConnectionStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/setup/status', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      setConnected(response.data.github_gitlab_connected);
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  const handleGitHubConnect = async () => {
    setConnecting(true);
    try {
      // This would redirect to GitHub OAuth or accept a Gist URL
      // For now, just mark as connected
      setConnected(true);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to connect');
    }
    setConnecting(false);
  };

  const handleSkip = () => {
    router.push('/dashboard');
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
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Phase 3: Connect GitHub/GitLab
            </h1>
            <p className="text-gray-600">
              Link your GitHub/GitLab account to access CI/CD error logs
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {connected && (
            <div className="mb-8 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-800 font-semibold">✓ GitHub connected successfully!</p>
            </div>
          )}

          <div className="space-y-6 mb-8">
            {/* Option 1: GitHub OAuth */}
            <div className="p-6 border-2 border-gray-200 rounded-lg hover:border-blue-300 transition">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Option 1: Connect with GitHub OAuth
              </h3>
              <p className="text-gray-600 mb-4">
                Authorize our app to access your GitHub repositories and CI/CD workflows.
                This gives us access to your error logs and allows for direct PR creation.
              </p>
              <button
                onClick={handleGitHubConnect}
                disabled={connecting || connected}
                className="px-6 py-2 bg-gray-800 hover:bg-gray-900 disabled:bg-gray-400 text-white font-semibold rounded-lg transition"
              >
                {connecting ? 'Connecting...' : connected ? 'Connected' : 'Connect with GitHub'}
              </button>
            </div>

            {/* Option 2: Upload Error Log */}
            <div className="p-6 border-2 border-gray-200 rounded-lg hover:border-blue-300 transition">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Option 2: Upload Error Log Directly
              </h3>
              <p className="text-gray-600 mb-4">
                Don't want to authorize GitHub? You can drag and drop error log files directly
                from your CI/CD pipeline. Supported formats: .log, .txt, .json
              </p>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition cursor-pointer">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20m-12-8v12m0 0l-4-4m4 4l4-4"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p className="mt-2 text-sm text-gray-600">
                  Drag and drop error logs here, or{' '}
                  <span className="text-blue-600 font-semibold">click to browse</span>
                </p>
              </div>
            </div>
          </div>

          {/* Benefits Section */}
          <div className="p-6 bg-blue-50 rounded-lg mb-8">
            <h3 className="font-semibold text-gray-900 mb-3">Why connect your source?</h3>
            <ul className="space-y-2 text-gray-700">
              <li>✓ Automatic error detection from CI/CD logs</li>
              <li>✓ AI-powered fix recommendations</li>
              <li>✓ One-click PR creation with suggested fixes</li>
              <li>✓ Integration with your workflow</li>
            </ul>
          </div>

          {/* Navigation */}
          <div className="flex gap-4">
            <button
              onClick={handleSkip}
              className="flex-1 px-6 py-3 bg-gray-400 hover:bg-gray-500 text-white font-semibold rounded-lg transition"
            >
              Skip for Now
            </button>
            {connected && (
              <button
                onClick={() => router.push('/dashboard')}
                className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition"
              >
                Go to Dashboard
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
