# RAG CI/CD Frontend

Next.js frontend for the RAG CI/CD error analysis system with GitHub OAuth authentication and analysis dashboard.

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **NextAuth.js** - Authentication with GitHub OAuth
- **Axios** - HTTP client for API calls

## Features

- ✅ GitHub OAuth authentication
- ✅ CI/CD log analysis interface
- ✅ Results dashboard with confidence scores
- ✅ Pull request creation integration (coming soon)
- ✅ Analysis history
- ✅ Real-time status updates

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure GitHub OAuth

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App with:
   - Homepage URL: `http://localhost:3000`
   - Callback URL: `http://localhost:3000/api/auth/callback/github`
3. Copy the Client ID and Client Secret

### 3. Environment Variables

Create `.env.local`:

```bash
cp .env.example .env.local
```

Fill in:

```env
GITHUB_ID=your_github_client_id
GITHUB_SECRET=your_github_client_secret
NEXTAUTH_SECRET=openssl rand -base64 32  # Generate a random key
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
app/
├── api/
│   └── auth/[...nextauth]/route.ts    # NextAuth configuration
├── auth/
│   └── github/page.tsx                 # GitHub OAuth redirect
├── dashboard/
│   └── page.tsx                        # Main analysis dashboard
├── layout.tsx                          # Root layout with metadata
├── page.tsx                            # Home/login page
└── globals.css                         # Global Tailwind styles
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`. Key endpoints:

- `POST /api/analyze` - Submit logs for analysis
- `GET /api/analyses` - Fetch analysis history
- `POST /api/pull-requests` - Create a PR with fixes (coming soon)

## Building for Production

```bash
npm run build
npm start
```

## Next Steps (Phase 2 Roadmap)

- [ ] PR creation and auto-submission
- [ ] Diff viewer for suggested fixes
- [ ] Repository integration
- [ ] Analysis caching and history
- [ ] Email notifications
- [ ] Deployment to production

## Documentation

See the backend documentation at `/docs` for API specifications.
