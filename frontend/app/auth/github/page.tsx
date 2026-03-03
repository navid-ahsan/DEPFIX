'use client';

import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function GitHubAuth() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSignIn = async () => {
    setLoading(true);
    try {
      const result = await signIn('github', { redirect: false });
      
      if (result?.error) {
        setError('Authentication failed. Please try again.');
        setLoading(false);
      } else if (result?.ok) {
        // Redirect to dashboard after successful auth
        router.push('/dashboard');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
      setLoading(false);
    }
  };

  const handleCancel = () => {
    router.push('/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center max-w-md mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {error ? (
            <>
              <h1 className="text-2xl font-bold text-red-600 mb-4">
                Authentication Failed
              </h1>
              <p className="text-gray-600 mb-6">
                {error}
              </p>
              <div className="space-y-3">
                <button
                  onClick={handleSignIn}
                  disabled={loading}
                  className="w-full bg-gray-800 hover:bg-gray-900 disabled:bg-gray-400 text-white font-bold py-2 px-6 rounded transition duration-200"
                >
                  {loading ? 'Signing in...' : 'Try Again'}
                </button>
                <button
                  onClick={handleCancel}
                  className="w-full bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 px-6 rounded transition duration-200"
                >
                  Back to Home
                </button>
              </div>
            </>
          ) : loading ? (
            <>
              <h1 className="text-2xl font-bold text-gray-900 mb-4">
                Authenticating...
              </h1>
              <p className="text-gray-600 mb-6">
                Redirecting to GitHub login
              </p>
              <div className="flex justify-center mb-6">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
              <button
                onClick={handleCancel}
                className="w-full bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 px-6 rounded transition duration-200"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-gray-900 mb-4">
                Sign in with GitHub
              </h1>
              <p className="text-gray-600 mb-6">
                Connect your GitHub account to get started with RAG CI/CD Analysis
              </p>
              <div className="space-y-3">
                <button
                  onClick={handleSignIn}
                  disabled={loading}
                  className="w-full bg-gray-800 hover:bg-gray-900 disabled:bg-gray-400 text-white font-bold py-2 px-6 rounded transition duration-200"
                >
                  {loading ? 'Signing in...' : 'Sign in with GitHub'}
                </button>
                <button
                  onClick={handleCancel}
                  className="w-full bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 px-6 rounded transition duration-200"
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
