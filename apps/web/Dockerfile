FROM node:20-alpine AS base
WORKDIR /app

# --- Dependencies ---
FROM base AS deps
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci

# --- Build ---
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
ARG NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
ENV NEXT_PUBLIC_CLERK_SIGN_IN_URL=${NEXT_PUBLIC_CLERK_SIGN_IN_URL}
ENV NEXT_PUBLIC_CLERK_SIGN_UP_URL=${NEXT_PUBLIC_CLERK_SIGN_UP_URL}

RUN npm run build

# --- Production ---
FROM base AS runner
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
