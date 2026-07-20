# PielSana IA — Guía para el agente

MVP de análisis de piel por IA. El usuario sube una foto y recibe una clasificación de condiciones
cutáneas (lunares/HAM10000, acné, rosácea) generada por modelos locales Keras, enriquecida con
explicaciones y recomendaciones vía **DeepSeek** (texto). La detección automática desde la imagen
(endpoint de visión) usa **OpenAI gpt-4o** y es opcional (DeepSeek no acepta imágenes por API).

Monorepo con dos servicios independientes que se comunican por HTTP: `backend/` (FastAPI, Python
3.10) y `frontend/` (React 18 + TypeScript + Vite + Tailwind).

> **Contexto clínico:** es una herramienta educativa/de autocuidado, **no** un diagnóstico médico.
> Todo texto orientado al usuario debe recordar que no sustituye a un dermatólogo.

## Dónde está cada cosa

Al trabajar dentro de `backend/` o `frontend/` se cargan solos los `CLAUDE.md` de esas carpetas, con
las convenciones del servicio. Lo demás se lee cuando hace falta:

| Necesito… | Leer |
|---|---|
| Convenciones del backend, endpoints, modelos Keras | `backend/CLAUDE.md` *(automático)* |
| Convenciones del frontend, capas, Tailwind, assets | `frontend/CLAUDE.md` *(automático)* |
| Estructura general, comandos, variables de entorno | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) |
| Desplegar (Vercel + VPS, Nginx, DuckDNS, HTTPS) | [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md) |
| Deuda técnica: hallazgos numerados, pendientes y resueltos | [`docs/AUDITORIA.md`](docs/AUDITORIA.md) |

Antes de encarar mejoras, consultar [`docs/AUDITORIA.md`](docs/AUDITORIA.md) y marcar los ítems al
resolverlos.

## Reglas que aplican siempre

- **Nunca loguear `DEEPSEEK_API_KEY` ni `OPENAI_API_KEY`**, ni exponerlas en respuestas de la API.
  El proveedor de texto es DeepSeek; OpenAI solo se usa para el endpoint de visión.
- **Nunca devolver detalles de excepción al cliente**: van al log, no al `detail` de la respuesta —
  filtran rutas y versiones.
- El código, comentarios, labels y mensajes de la API están en **español**; mantener ese idioma.
- No agregar disclaimers médicos de más ni cambiar el tono; PielSana IA insiste en privacidad (las
  imágenes se procesan de forma temporal y **no se almacenan**).
- Los modelos `.keras` **no están en el repo** (gitignored). Sin ellos los endpoints de predicción
  responden 500; no es un bug que haya que "arreglar".
- **Producción está rota por *mixed content***: el frontend se sirve por HTTPS y el backend por HTTP.
  Detalle y plan en [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

## Git

- No añadir el trailer `Co-Authored-By: Claude` en los commits.
