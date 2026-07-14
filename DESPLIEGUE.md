# Despliegue de PielSana IA

Guía de despliegue. **Frontend en Vercel**, **backend en un VPS (Hetzner)** detrás de HTTPS.

> Los bloques de `docker-compose.yml` y Nginx de acá son **documentación** para copiar al
> servidor; no son archivos versionados del repo. Ajustá los placeholders
> (`SUBDOMINIO.duckdns.org`, `TU-APP.vercel.app`) a tus valores reales.

## Topología

```
Vercel (frontend React/Vite, HTTPS)
   │  fetch  ${VITE_API_URL}/skin/...
   ▼
Hetzner VPS  →  Nginx (443, TLS Let's Encrypt)  →  backend FastAPI (:8080, Docker)
                                                     ├── modelos Keras (CPU)
                                                     ├── DeepSeek  (texto)
                                                     └── OpenAI gpt-4o (visión, opcional)
```

El orden importa por el CORS: primero el backend con su URL HTTPS, después Vercel, y al final
se completa `FRONTEND_ORIGINS` con la URL final de Vercel.

---

## 1. Frontend — Vercel

1. Importar el repo en Vercel.
2. **Root Directory:** `frontend/`.
3. **Build Command:** `npm run build` · **Output Directory:** `dist`.
4. **Environment Variables:**
   - `VITE_API_URL = https://SUBDOMINIO.duckdns.org` (la URL HTTPS del backend, paso 2).
   - `VITE_BASE = /` (con Vercel el sitio va en la raíz; no hace falta subruta).
5. Deploy. Vercel entrega una URL `https://TU-APP.vercel.app` → usála en `FRONTEND_ORIGINS` (paso 2.6).

> Si el backend todavía no tiene HTTPS, dejá `VITE_API_URL` con la URL DuckDNS ya planificada
> y redeployá cuando el backend esté arriba.

---

## 2. Backend — Hetzner VPS

### 2.1 Provisionar el VPS
- **Hetzner Cloud CX22** (2 vCPU, 4 GB RAM) — 4 GB para que TensorFlow cargue los 3 modelos sin ahogarse.
- Imagen **Ubuntu 24.04**, ubicación **Ashburn (US)** si el público es de Argentina.
- Subir tu **clave SSH** al crear el server.

### 2.2 DNS / HTTPS gratis con DuckDNS
1. Crear un subdominio en https://www.duckdns.org (`SUBDOMINIO.duckdns.org`).
2. Apuntarlo a la **IP pública** del VPS (campo *current ip* en DuckDNS).
3. Verificar: `dig +short SUBDOMINIO.duckdns.org` debe devolver la IP del VPS.

### 2.3 Instalar Docker + Compose
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
```

### 2.4 Traer el código y los modelos
```bash
git clone https://github.com/thejoresp/PielSanaIA-MVP.git
cd PielSanaIA-MVP
```
Los `.keras` **no están en git**. Copiarlos desde tu máquina (sin ellos → 500):
```bash
scp -r backend/modelos/* root@IP_DEL_VPS:~/PielSanaIA-MVP/backend/modelos/
# estructura esperada:
#   backend/modelos/ham10000/lunares.keras
#   backend/modelos/acne/acne.keras
#   backend/modelos/rosacea/rosacea.keras
```

### 2.5 Crear el `.env` (en la raíz del repo, en el server)
```env
DEEPSEEK_API_KEY=sk-...                       # requerida (texto)
# OPENAI_API_KEY=sk-...                        # opcional (solo detección por imagen)
FRONTEND_ORIGINS=https://TU-APP.vercel.app     # se completa tras el deploy de Vercel
```

### 2.6 `docker-compose.yml` (crear en el server)
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env
    volumes:
      - ./backend/modelos:/app/backend/modelos:ro
    restart: unless-stopped
    expose:
      - "8080"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - backend
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    # Renovación automática cada 12 h
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

### 2.7 `nginx.conf` (crear en el server)
```nginx
server {
    listen 80;
    server_name SUBDOMINIO.duckdns.org;

    # Validación ACME (Let's Encrypt)
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    # Todo lo demás va a HTTPS
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    server_name SUBDOMINIO.duckdns.org;

    ssl_certificate     /etc/letsencrypt/live/SUBDOMINIO.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/SUBDOMINIO.duckdns.org/privkey.pem;

    client_max_body_size 10M;   # el backend valida 8 MB; dejar un margen

    location / {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2.8 Emitir el certificado (primera vez)
El bloque `ssl_certificate` aún no existe, así que se emite en dos pasos:
```bash
# 1) Levantar solo backend + nginx con un nginx temporal solo-HTTP
#    (comentá el bloque 'server 443' de nginx.conf para el primer arranque)
docker compose up -d backend nginx

# 2) Pedir el certificado por HTTP-01
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d SUBDOMINIO.duckdns.org --email TU_EMAIL --agree-tos --no-eff-email

# 3) Descomentar el bloque 443 en nginx.conf y recargar todo
docker compose up -d
```

### 2.9 Levantar todo
```bash
docker compose up -d --build
docker compose logs -f backend   # verificar que los modelos cargan
```

Probar: `curl https://SUBDOMINIO.duckdns.org/skin/api/condition/acne` → JSON 200.

---

## 3. Cierre (glue)

1. En Vercel: `VITE_API_URL = https://SUBDOMINIO.duckdns.org` → redeploy.
2. En el `.env` del VPS: `FRONTEND_ORIGINS = https://TU-APP.vercel.app` → `docker compose up -d backend`.
3. Abrir la app en Vercel y probar el flujo completo (subir imagen → resultado).
4. Actualizar el email de contacto del modal de consentimiento (`ImageUploader.tsx`),
   que apunta al dominio vencido `contacto@pielsanaia.click`.

## Checklist rápido

- [ ] VPS Hetzner CX22 (Ubuntu, SSH key)
- [ ] Subdominio DuckDNS → IP del VPS
- [ ] Docker + Compose instalados
- [ ] Modelos `.keras` copiados por `scp`
- [ ] `.env` con `DEEPSEEK_API_KEY` (+ `OPENAI_API_KEY` opcional)
- [ ] Certificado Let's Encrypt emitido
- [ ] `docker compose up -d` → backend en HTTPS
- [ ] Vercel con `VITE_API_URL` + `VITE_BASE=/`
- [ ] `FRONTEND_ORIGINS` con la URL de Vercel
- [ ] Flujo end-to-end probado
- [ ] Email de contacto actualizado
