# Next.js on Cloud Run (forgiving COPY patterns)

FROM node:20-slim AS deps
WORKDIR /app
# Copy package.json (and package-lock.json if it exists)
COPY package*.json ./
RUN npm install --no-audit --no-fund

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8080
# Copy built app and runtime deps
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
CMD ["npm","start"]
