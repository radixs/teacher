# syntax=docker/dockerfile:1.6

FROM node:20-alpine AS base

WORKDIR /usr/src/app

# Install dependencies at build time for caching benefits when using image directly
COPY app/package*.json ./
RUN npm install --no-audit --no-fund

# Copy source
COPY app .

ENV FRONTEND_INTERNAL_PORT=3000

EXPOSE 3000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
