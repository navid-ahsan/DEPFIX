FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies
RUN npm ci --omit=dev

# Copy all source files
COPY . .

# If .next doesn't exist, build it now
RUN if [ ! -d ".next" ]; then npm ci && npm run build; fi

# Expose port
EXPOSE 3000

# Environment variables  
ENV NODE_ENV=production
ENV NEXT_PUBLIC_API_URL=http://backend:8000
ENV NEXTAUTH_URL=http://localhost:3000
ENV PORT=3000

# Start Next.js
CMD ["npm", "start"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

# Start Next.js app
CMD ["npm", "start"]
