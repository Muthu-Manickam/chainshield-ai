FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npx vite build
ENV API_URL=http://api:8000
EXPOSE 4173
CMD ["npx", "vite", "preview", "--host", "--port", "4173"]
