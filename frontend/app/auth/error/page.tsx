'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function AuthError() {
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(searchParams.get('error'));
  }, [searchParams]);

  const errorMessages: { [key: string]: string } = {
    OAuthAccountNotLinked: 'This email is already registered with another provider',
    OAuthCallback: 'Error during authentication. Please try again.',
    OAuthSignin: 'Error signing in. Please try again.',
    OAuthCreateAccount: 'Could not create user account',
    EmailCreateAccount: 'Could not create user with this email',
    Callback: 'Error in authentication callback',
    EmailSignInError: 'Email provider is not enabled',
    CredentialsSignin: 'Authorization failed. Check your credentials.',
  };

  const message = error ? errorMessages[error] || 'An authentication error occurred' : 'Unknown error';

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center max-w-md mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-red-600 mb-4">
            Authentication Error
          </h1>
          <p className="text-gray-600 mb-8">
            {message}
          </p>
          <div className="space-y-3">
            <Link
              href="/"
              className="block bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded transition duration-200"
            >
              Back to Home
            </Link>
            <Link
              href="/auth/github"
              className="block bg-gray-800 hover:bg-gray-900 text-white font-bold py-2 px-6 rounded transition duration-200"
            >
              Try Again
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
