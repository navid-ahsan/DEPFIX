'use client';

import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function GitHubAuth() {
  const router = useRouter();

  useEffect(() => {
    signIn('github', { redirect: false }).then((result) => {
      if (result?.ok) {
        router.push('/dashboard');
      }
    });
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Authenticating...
        </h1>
        <p className="text-gray-600">
          Redirecting to GitHub login
        </p>
        <div className="mt-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      </div>
    </div>
  );
}
