# Multi-stage Dockerfile for Epoxa Supervisor Dashboard
FROM node:22-alpine AS builder

WORKDIR /app

RUN corepack enable pnpm

COPY pnpm-workspace.yaml package.json pnpm-lock.yaml* ./
COPY packages/ui-tokens ./packages/ui-tokens
COPY packages/api-client ./packages/api-client
COPY apps/dashboard ./apps/dashboard

RUN pnpm install --frozen-lockfile || pnpm install
RUN pnpm --filter epoxa-dashboard build

# Final Serving Stage with non-root Nginx
FROM nginxinc/nginx-unprivileged:alpine AS runner

COPY --from=builder /app/apps/dashboard/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
