# Frontend statis (ES module tanpa build), disajikan nginx.
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx-aman.conf /etc/nginx/aman.conf
COPY index.html /usr/share/nginx/html/
COPY src /usr/share/nginx/html/src
COPY assets /usr/share/nginx/html/assets
EXPOSE 80
