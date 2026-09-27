FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build


FROM nginx:stable-alpine

ENV TRUSTED_PROXY_CIDR=127.0.0.1/32

COPY nginx.conf /etc/nginx/templates/default.conf.template

COPY --from=build /app/dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
