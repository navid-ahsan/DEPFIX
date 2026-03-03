import Link from 'next/link';
import { redirect } from 'next/navigation';
import { auth } from '@/lib/auth';

export default async function Home() {
  // Check if user is already authenticated
  const session = await auth();
  
  if (session) {
    redirect('/dashboard');
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center max-w-2xl mx-auto px-4">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          RAG CI/CD Analysis
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Intelligent error analysis and automatic fix generation for your CI/CD pipelines
        </p>
        
        <div className="space-y-4 mb-8">
          <Link
            href="/auth/signin"
            className="inline-block bg-gray-800 hover:bg-gray-900 text-white font-bold py-3 px-8 rounded-lg transition duration-200 transform hover:scale-105 w-full sm:w-auto"
          >
            Get Started
          </Link>
          
          <p className="text-sm text-gray-600">
            Sign in with GitHub or use a test account
          </p>
        </div>

        <div className="mt-12 pt-12 border-t border-gray-300">
          <h2 className="text-lg font-semibold text-gray-800 mb-6">Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg p-6 shadow-md">
              <h3 className="font-bold text-gray-900 mb-2">Error Analysis</h3>
              <p className="text-gray-600 text-sm">
                Automatically extract and analyze errors from CI/CD logs
              </p>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-md">
              <h3 className="font-bold text-gray-900 mb-2">AI-Powered Fixes</h3>
              <p className="text-gray-600 text-sm">
                Get intelligent solutions using RAG and LLMs
              </p>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-md">
              <h3 className="font-bold text-gray-900 mb-2">Auto PR Creation</h3>
              <p className="text-gray-600 text-sm">
                Automatically create pull requests with fixes
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
