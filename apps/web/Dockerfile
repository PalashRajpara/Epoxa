# Multi-stage Dockerfile for Epoxa Customer Web App
FROM node:22-alpine AS builder

WORKDIR /app

RUN corepack enable pnpm

COPY pnpm-workspace.yaml package.json pnpm-lock.yaml* ./
COPY packages/ui-tokens ./packages/ui-tokens
COPY packages/api-client ./packages/api-client
COPY apps/web ./apps/web

RUN pnpm install --frozen-lockfile || pnpm install
RUN pnpm --filter epoxa-web build

# Final Serving Stage with non-root Nginx
FROM nginxinc/nginx-unprivileged:alpine AS runner

COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
