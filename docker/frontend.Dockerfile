# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
EXPOSE 5173
# The documented demo uses Vite so Settings retains its simulator controls.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
