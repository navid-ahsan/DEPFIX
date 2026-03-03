'use client';

import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function GitHubAuth() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleAuth = async () => {
      try {
        const result = await signIn('github', { redirect: false });
        
        if (result?.error) {
          setError('Authentication failed. Please try again.');
        } else if (result?.ok) {
          // Redirect to dashboard after successful auth
          router.push('/dashboard');
        }
      } catch (err) {
        setError('An error occurred. Please try again.');
      }
    };

    handleAuth();
  }, [router]);

  const handleCancel = () => {
    router.push('/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center max-w-md mx-auto px-4">
        {error ? (
          <>
            <h1 className="text-2xl font-bold text-red-600 mb-4">
              Authentication Failed
            </h1>
            <p className="text-gray-600 mb-6">
              {error}
            </p>
            <button
              onClick={handleCancel}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded transition duration-200"
            >
              Back to Home
            </button>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Authenticating...
            </h1>
            <p className="text-gray-600 mb-6">
              Redirecting to GitHub login
            </p>
            <div className="mt-8 flex flex-col items-center gap-6">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <button
                onClick={handleCancel}
                className="bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 px-6 rounded transition duration-200"
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
