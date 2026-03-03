'use client';

import { signIn } from 'next-auth/react';
import { useState } from 'react';

export default function SignIn() {
  const [testEmail, setTestEmail] = useState('test@example.com');
  const [testPassword, setTestPassword] = useState('test123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTestLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await signIn('credentials', {
        email: testEmail,
        password: testPassword,
        redirect: true,
        callbackUrl: '/dashboard',
      });

      if (result?.error) {
        setError('Invalid test credentials. Use test@example.com / test123');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGitHubLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await signIn('github', {
        redirect: true,
        callbackUrl: '/dashboard',
      });
    } catch (err) {
      setError('GitHub authentication failed.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="w-full max-w-md mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
            RAG CI/CD
          </h1>
          <p className="text-center text-gray-600 mb-8">
            Sign in to your account
          </p>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* GitHub Login */}
          <div className="mb-6">
            <button
              onClick={handleGitHubLogin}
              disabled={loading}
              className="w-full bg-gray-800 hover:bg-gray-900 disabled:bg-gray-400 text-white font-bold py-2 px-4 rounded transition duration-200"
            >
              {loading ? 'Signing in...' : 'Sign in with GitHub'}
            </button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Or test with demo account</span>
            </div>
          </div>

          {/* Test Login */}
          <form onSubmit={handleTestLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                disabled={loading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent disabled:bg-gray-100"
                placeholder="test@example.com"
              />
              <p className="text-xs text-gray-500 mt-1">Demo: test@example.com</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={testPassword}
                onChange={(e) => setTestPassword(e.target.value)}
                disabled={loading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent disabled:bg-gray-100"
                placeholder="test123"
              />
              <p className="text-xs text-gray-500 mt-1">Demo: test123</p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-2 px-4 rounded transition duration-200"
            >
              {loading ? 'Signing in...' : 'Sign in with Test Account'}
            </button>
          </form>

          <p className="text-xs text-gray-500 text-center mt-6">
            Use the test account to bypass GitHub rate limits during development
          </p>
        </div>
      </div>
    </div>
  );
}
