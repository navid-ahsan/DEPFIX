import { getServerSession } from 'next-auth/next';
import GitHubProvider from 'next-auth/providers/github';
import CredentialsProvider from 'next-auth/providers/credentials';

const authOptions = {
  providers: [
    // GitHub Provider (for production)
    GitHubProvider({
      clientId: process.env.GITHUB_ID || '',
      clientSecret: process.env.GITHUB_SECRET || '',
    }),
    // Test/Dev Provider (for testing without GitHub rate limits)
    CredentialsProvider({
      name: 'Test Account',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'test@example.com' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        // Simple test credentials for development
        if (
          credentials?.email === 'test@example.com' &&
          credentials?.password === 'test123'
        ) {
          return {
            id: '1',
            name: 'Test User',
            email: credentials.email,
            image: 'https://avatars.githubusercontent.com/u/1?v=4',
          };
        }
        return null;
      },
    }),
  ],
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
};

export const auth = () => getServerSession(authOptions as any);



