import { getServerSession } from 'next-auth/next';
import GitHubProvider from 'next-auth/providers/github';

const authOptions = {
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_ID || '',
      clientSecret: process.env.GITHUB_SECRET || '',
    }),
  ],
  pages: {
    signIn: '/auth/github',
    error: '/auth/error',
  },
};

export const auth = () => getServerSession(authOptions as any);


