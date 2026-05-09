FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
ARG NPM_REGISTRY=https://registry.npmjs.org/
RUN npm ci --registry="${NPM_REGISTRY}"

COPY . .
ARG VITE_MAP_TILE_URL
ARG VITE_MAP_TILE_SUBDOMAINS
ARG VITE_MAP_COORDINATE_SYSTEM
ENV VITE_MAP_TILE_URL=${VITE_MAP_TILE_URL}
ENV VITE_MAP_TILE_SUBDOMAINS=${VITE_MAP_TILE_SUBDOMAINS}
ENV VITE_MAP_COORDINATE_SYSTEM=${VITE_MAP_COORDINATE_SYSTEM}
RUN npm run build

FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/10-basic-auth.sh /docker-entrypoint.d/10-basic-auth.sh
COPY --from=build /app/dist /usr/share/nginx/html/dashboard

RUN chmod +x /docker-entrypoint.d/10-basic-auth.sh

EXPOSE 80
