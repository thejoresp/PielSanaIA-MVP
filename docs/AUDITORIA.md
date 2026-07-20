# Auditoría técnica — PielSana IA

> Auditoría completa del código realizada el **2026-07-19** sobre la rama `add-claude-config`
> (commit `742a2dc`). Se revisó el 100% del backend (7 archivos Python), el 100% del frontend
> (`src/` + configuración) y la infraestructura versionada.
>
> Complementa `CLAUDE.md` (raíz) y `docs/ARQUITECTURA.md` (arquitectura). Este documento es la
> **única lista de trabajo pendiente** del proyecto: marcar los checkboxes al resolver cada punto
> y anotar el commit correspondiente.

**Severidades:** 🔴 rompe la app, filtra datos o cuesta dinero · 🟡 degrada calidad/mantenibilidad ·
⚪ cosmético o limpieza.

> **Cómo leer los ítems resueltos:** el cuerpo de cada hallazgo conserva la descripción y las
> rutas/líneas **del momento de la auditoría**, para dejar constancia de qué se encontró. La línea
> del checkbox dice cómo quedó. Si un ítem `[x]` menciona un archivo que ya no existe
> (p. ej. `components/ImageUploader.tsx:330`), es historia, no un pendiente. Los ítems **abiertos**
> sí apuntan a rutas vigentes.

---

## Estado — 2026-07-19

**Resueltos (33):** A1, A2, A3, A4, A5, A6, A7, A8, A9 *(parcial)*, A10, A12, A13, A14, A15,
B5, C1, C2, C3, C4, C5, C8, C9, C10, C11, C12, C13 *(parcial)*, C14, C15, C16, C17, C18, S9, S12.

### Qué queda, por prioridad

| Orden | Ítem | Por qué | Esfuerzo |
|-------|------|---------|----------|
| 1 | [S1](#s1) / [S2](#s2) / [S3](#s3) — `<head>` del `index.html` | Cambia cómo se ve la app compartida por WhatsApp | 30 min |
| 2 | [C6](#c6) / [C7](#c7) — política de privacidad + contacto real | Hueco legal (Ley 25.326, datos sensibles) | 2 h |
| 3 | [D4](#d4) — CI | Los tests existen y no los corre nadie | 30 min |
| 4 | [B1](#b1) — verificar el preprocesado contra el notebook | Un modelo "que anda pero mal" no se nota desde la app | 1 h |
| 5 | [B2](#b2) / [B3](#b3) — umbral de confianza y clases malignas | Delicado en una herramienta de salud | 2 h |
| 6 | [D1](#d1) / [D2](#d2) / [D3](#d3) — `.dockerignore`, multi-stage, HEALTHCHECK | [A7](#a7) ya destrabó el HEALTHCHECK | 1 h |
| 7 | [C19](#c19) — gh-pages vs Vercel en `package.json` | Dos caminos de deploy conviven; solo uno es el vigente | 10 min |
| 8 | [S4](#s4) — prerenderizado | Sin esto, [S3](#s3) no se ve en WhatsApp. **Más barato ahora:** con [S9](#s9) resuelto, `/conditions/*` ya renderiza sin backend | 2-3 h |

**Bloqueado por datos del usuario:** [C7](#c7) (email de contacto definitivo), y todo el bloque de
despliegue de `DESPLIEGUE.md` (subdominio DuckDNS, URL de Vercel → `FRONTEND_ORIGINS`).

### Verificación de esta tanda

- ✅ Frontend: `tsc --noEmit`, `eslint` y `npm run build` limpios. Bundle inicial
  **218.57 KB → 186.57 KB** ([C9](#c9) + [S12](#s12) + [S9](#s9)).
- ✅ **Probado en el navegador** (`npm run dev`): el home renderiza las 4 tarjetas del catálogo,
  el modal de consentimiento abre con "Aceptar" deshabilitado hasta tildar, y la ruta lazy
  `/results-openai` carga y muestra el estado vacío. Sin errores en consola.
- ✅ **`/conditions/rosacea` renderiza completa con el backend apagado** — es la comprobación de
  [S9](#s9): antes esa página quedaba vacía sin API.
- ✅ [A13](#a13) confirmado empíricamente con Pillow: un PNG 8000×8000 pesa **193 KB**, pasa el
  filtro de 8 MB y `verify()` no lo detecta.
- ⚠️ **`pytest` NO se ejecutó**: no hay venv en el repo y el Python del sistema es 3.13, donde
  TensorFlow 2.19 no tiene wheels. Los tests nuevos (bomba de descompresión, `content_type`,
  prompt injection, `/health`) están **sin correr**. Ver [D4](#d4).

---

## 1. Backend — API (FastAPI)

### <a id="a1"></a>🔴 A1 · La inferencia bloquea el event loop
- [x] Resuelto — `run_in_threadpool` en `analizar_con_modelo()` y en las dos llamadas a IA

`analizar_con_modelo()` está declarada `async def` pero llama de forma síncrona a
`predict_fn()` → `model.predict()` (`backend/controllers/skin.py:64`), que es CPU-bound.
En asyncio eso **congela el proceso entero** mientras dura la predicción: con dos usuarios
concurrentes, el segundo espera con la app bloqueada (health checks incluidos).

```python
from fastapi.concurrency import run_in_threadpool
pred_label, probabilities = await run_in_threadpool(predict_fn, image_bytes)
```

Es el problema de arquitectura más real del backend hoy.

### <a id="a2"></a>🔴 A2 · Endpoints de IA sin rate limiting
- [x] Resuelto — `slowapi`: 20/min en los endpoints de modelo, 10/min en los de IA

`/skin/openai-analizar` (gpt-4o, pago por imagen) y `/skin/openai-recomendaciones` (DeepSeek)
no tienen ningún límite. **CORS no protege**: es una restricción del navegador, con `curl` se
saltea. La URL del backend va a estar pública dentro del bundle del frontend.

Mínimo: `slowapi` con límite por IP (p. ej. 10/min) en esos dos endpoints.

### <a id="a3"></a>🔴 A3 · Prompt injection y costo ilimitado en `/openai-recomendaciones`
- [x] Resuelto — allowlist de las 11 etiquetas vía `validator` de Pydantic v1 (422)

`PrediccionRequest.prediccion` es un `str` sin restricción (`skin.py:246`) que se interpola
directo en el prompt (`skin.py:337`). Se puede enviar texto arbitrario y de cualquier tamaño
("ignorá lo anterior y…") y el costo en tokens lo paga el proyecto.

Validar contra la lista blanca de las 11 etiquetas conocidas, o como mínimo
`constr(max_length=100)` (**sintaxis Pydantic v1**).

### <a id="a4"></a>🟡 A4 · Fuga de detalles internos en los mensajes de error
- [x] Resuelto — mensaje genérico al cliente, `logger.exception` del lado del servidor

`detail=f"...{str(e)}"` en `skin.py:67` y `skin.py:269` devuelve al cliente el mensaje de
excepción de TensorFlow/Python (rutas del filesystem, versiones de librerías).
Devolver un mensaje genérico y loguear el detalle del lado del servidor.

### <a id="a5"></a>🟡 A5 · `print()` usado como logging
- [x] Resuelto — `logging` en los tres módulos; cero `print` en `backend/`. Nivel por `LOG_LEVEL`

`skin.py:66,99,260,268` y **12 ocurrencias** en `skin_analysis_service.py`. Sin timestamps,
sin niveles, imposible de silenciar o filtrar en producción. Migrar a
`logging.getLogger(__name__)`.

### <a id="a6"></a>🟡 A6 · Carga perezosa de modelos sin lock ni warmup
- [x] Resuelto — `_ModeloKeras` con `threading.Lock` + doble chequeo, y warmup en el `startup`

`load_lunares_model()` (`skin_analysis_service.py:31`, y sus gemelas de acné/rosácea) chequea
`if MODEL is None` sin candado: dos requests concurrentes durante el arranque cargan el modelo
**dos veces** → pico de RAM duplicado, crítico en un VPS de 4 GB con 3 modelos TensorFlow.
Además el primer usuario paga toda la carga.

Solución: cargar en `@app.on_event("startup")` (o `lifespan`) y/o proteger con `threading.Lock`.

### <a id="a7"></a>🟡 A7 · No existe endpoint `/health`
- [x] Resuelto — `GET /health` con estado por modelo; `GET /` ya no redirige a un 404

Nginx, el `HEALTHCHECK` de Docker y cualquier monitor de uptime no tienen a qué apuntar.
Peor: `GET /` redirige a `/skin/` (`main.py:47`), que **siempre** devuelve 404 a propósito
(`skin.py:252`) — la raíz de la API responde con un error.

Reemplazar por `{"status": "ok", "version": "0.1.0"}`.

### <a id="a8"></a>🟡 A8 · Código muerto en el controlador
- [x] Resuelto — eliminados `/skin/upload`, `/skin/` y `/skin/results`

- `/skin/upload` (`skin.py:254-269`) duplica `/api/analyze` — nadie lo llama.
- `/skin/` (`skin.py:249`) y `/skin/results` (`skin.py:271`) son stubs que solo lanzan 404.

El frontend usa exclusivamente `/api/*` y `/openai-*`. Son ~30 líneas para borrar.

### <a id="a9"></a>🟡 A9 · `max_tokens=500` puede truncar el JSON de la IA
- [x] Resuelto **parcialmente** — `MAX_TOKENS_IA = 900`. **Pendiente:** `response_format={"type": "json_object"}`

`skin.py:97`. Una descripción más 5 recomendaciones en español entran muy justo. Si se corta,
`json.loads` falla y el usuario ve *"No se pudo generar la descripción"* sin explicación.

Subir a 800–1000 y usar `response_format={"type": "json_object"}` (soportado por DeepSeek y
OpenAI) en lugar del regex que limpia los bloques ```` ```json ````.

### <a id="a10"></a>⚪ A10 · `conditions_data` embebido en el controlador
- [x] Resuelto — el contenido terminó en el **frontend** (`src/data/condiciones.ts`), ver [S9](#s9). El endpoint y `backend/data/` se eliminaron

130 líneas de datos estáticos dentro de `skin.py:114-244`. El propio comentario del código lo
reconoce ("temporal, normalmente iría en un archivo aparte"). Mover a `backend/data/conditions.py`
o a un JSON. **Ver también [S9](#s9)**: probablemente convenga que estos datos vivan en el
frontend.

### <a id="a11"></a>⚪ A11 · Efectos secundarios al importar `model_config.py`
- [ ] Resuelto

`os.makedirs` y la configuración de threads de TensorFlow se ejecutan en el import
(`model_config.py:27-35`). Además `tf.config.set_visible_devices` lanza excepción si TF ya se
inicializó. Funciona hoy, pero es frágil.

### <a id="a12"></a>⚪ A12 · `_completar_chat` no valida la respuesta
- [x] Resuelto — se valida `response.choices` y se responde 502 si viene vacío

`skin.py:101` accede a `response.choices[0]` sin comprobar que la lista no esté vacía.

### <a id="a13"></a>🔴 A13 · Bomba de descompresión: OOM del servidor con un PNG chico
- [x] Resuelto — `MAX_IMAGE_PIXELS = 40 MP`, verificado antes de decodificar

`leer_imagen_validada()` limita **bytes** (8 MB, `skin.py:41`) pero **no píxeles**. El
`Image.open(...).verify()` de `skin.py:50` solo parsea las cabeceras: **no decodifica**. La
decodificación real ocurre después, en `_preprocesar_imagen()`
(`skin_analysis_service.py:10-14`), con `convert('RGB')` y `img_to_array()`.

Pillow admite hasta ~179M píxeles antes de lanzar `DecompressionBombError`; por debajo de ese
umbral solo emite un *warning*. Un PNG de un color sólido de 13000×13000 pesa unos cientos de KB
—pasa el filtro de 8 MB sin problema— y `img_to_array` produce un array float32 de **~2 GB**.
En el VPS de 4 GB con tres modelos TensorFlow residentes, eso es OOM-kill del contenedor.
**Un solo request, sin autenticación.**

```python
# en leer_imagen_validada, después del verify()
with Image.open(BytesIO(image_bytes)) as probe:
    if probe.width * probe.height > MAX_IMAGE_PIXELS:
        raise HTTPException(400, "La imagen tiene una resolución excesiva.")
```

Se agrava con [A6](#a6) (carga de modelos sin lock, que ya duplica el pico de RAM).

### <a id="a14"></a>🟡 A14 · `content_type` del cliente inyectado sin sanitizar en el data URL
- [x] Resuelto — allowlist `CONTENT_TYPES_PERMITIDOS` + normalización antes del data URL

`skin.py:304` arma `f"data:{file.content_type};base64,{image_base64}"`. `content_type` viene del
header multipart —controlado por el cliente— y solo se valida con `startswith("image/")`
(`skin.py:31`). Un valor como `image/png;foo=bar,X` se concatena sin escapar en el payload que
se envía a la API de OpenAI (servicio externo y pago).

Reemplazar el `startswith` por una allowlist: `{"image/jpeg", "image/png", "image/webp"}`.

### <a id="a15"></a>⚪ A15 · Cliente de IA sin timeout
- [x] Resuelto — `timeout=30` en el cliente

`_completar_chat()` (`skin.py:96`) construye el `OpenAI(...)` sin `timeout`. Si el proveedor
responde lento, el worker queda retenido. Pasar `timeout=30`.

---

## 2. Backend — modelos y ML

### <a id="b1"></a>🟡 B1 · Verificar que el preprocesado coincide con el entrenamiento
- [ ] Verificado

`_preprocesar_imagen()` normaliza con `/255.0` (`skin_analysis_service.py:14`). Eso es correcto
**solo si** los modelos se entrenaron con ese mismo escalado. Si salieron de un MobileNet/
EfficientNet con `preprocess_input` (rango `[-1, 1]`), las predicciones están sistemáticamente
sesgadas y no habría forma de notarlo desde la app.

**Contrastar contra el notebook de entrenamiento.** Es el tipo de bug que produce un modelo
"que anda pero mal".

### <a id="b2"></a>🟡 B2 · Sin umbral de confianza
- [ ] Resuelto

Un `argmax` de 0.28 se presenta exactamente igual que uno de 0.97: *"Afección detectada:
Melanoma"*. En una herramienta de salud es delicado.

Propuesta: si la probabilidad máxima < ~0.5, mostrar "resultado no concluyente, probá con otra
foto" en vez de una etiqueta.

### <a id="b3"></a>🟡 B3 · Las clases malignas se muestran igual que las benignas
- [ ] Resuelto

El modelo de lunares puede devolver `mel` (Melanoma), `bcc` (Carcinoma Basocelular) o `akiec`
(Queratosis Actínica) con la misma tarjeta azul que "Con acné". Conviene un tratamiento
diferenciado para esas clases: mensaje más enfático de consulta dermatológica inmediata,
sin caer en alarmismo ni en un diagnóstico.

### <a id="b4"></a>⚪ B4 · Las probabilidades se calculan pero nunca se muestran
- [ ] Resuelto

Los 4 endpoints devuelven `probabilidades`, y ninguna página del frontend las usa. O se muestran
(un gráfico de barras aporta transparencia y refuerza el carácter orientativo) o se dejan de
enviar.

### <a id="b5"></a>⚪ B5 · Typo en una etiqueta visible al usuario
- [x] Resuelto — `Lunar Común (Nevus)`

`'Lúnar Común (Nevus)'` (`skin_analysis_service.py:27`) — "lunar" no lleva tilde.

---

## 3. Frontend — bugs y calidad

### <a id="c1"></a>🔴 C1 · Backslashes literales rompen el SVG del spinner
- [x] Resuelto

`frontend/src/components/ImageUploader.tsx:330-331`:

```jsx
<svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white\" xmlns="...\" fill="none\" viewBox="0 0 24 24">
  <circle className="opacity-25\" cx="12\" cy="12\" r="10\" stroke="currentColor\" strokeWidth="4">
```

Las `\"` dentro de un string JSX son **backslashes literales**: la clase queda `text-white\`,
y los atributos `xmlns`, `fill`, `cx`, `cy`, `r` y `stroke` quedan mal formados. El spinner de
"Analizando…" se ve roto. Es residuo de un escapado automático.

### <a id="c2"></a>🟡 C2 · `alert()` como manejo de errores
- [x] Resuelto — `BannerError` en la UI leyendo el `detail` del backend; cero `alert()`

`ImageUploader.tsx:127` y `:209`. El backend devuelve mensajes útiles en `detail`
(413 "supera 8 MB", 503 "IA no configurada", 502 "no se pudo contactar") y todos se descartan
a favor de un genérico *"Error al analizar la imagen"*.

Leer `data.detail` y mostrarlo en un banner dentro de la UI.

### <a id="c3"></a>🟡 C3 · `BrowserRouter` sin `basename`
- [x] Resuelto — `basename={import.meta.env.BASE_URL}`

`main.tsx:11`. Si se usa `VITE_BASE=/PielSanaIA-MVP/` (opción documentada en
`frontend/.env.example` para GitHub Pages), los assets cargan pero **el ruteo se rompe**.

```jsx
<BrowserRouter basename={import.meta.env.BASE_URL}>
```

### <a id="c4"></a>🟡 C4 · Sin validación de `VITE_API_URL`
- [x] Resuelto — aviso explícito por consola en `api/client.ts` si falta la variable

Si la variable falta en build time, todas las peticiones van a `undefined/skin/...` y fallan en
silencio. Un `console.error` explícito en `main.tsx` ahorra horas de debugging post-deploy.

### <a id="c5"></a>🟡 C5 · Sin ErrorBoundary
- [x] Resuelto — `components/ErrorBoundary.tsx`, montado en `main.tsx`

Cualquier excepción durante el render deja pantalla en blanco, sin mensaje ni forma de volver.

### <a id="c6"></a>🟡 C6 · Link "Política de Privacidad" muerto
- [ ] Resuelto

`Footer.tsx:34` apunta a `#privacy`, que no existe. La app procesa **datos biométricos
sensibles** y cita la Ley 25.326 en el modal de consentimiento: no tener la política publicada
es el hueco legal más visible. Debería ser una ruta real `/privacidad`.

### <a id="c7"></a>🟡 C7 · Datos de contacto falsos o muertos en producción
- [x] Resuelto

El contacto es ahora **`thejoresp@gmail.com`**, unificado en los tres lugares donde aparecía algo
distinto: el footer, la constante `CONTACTO_DATOS` de `components/upload/ConsentModal.tsx` (el canal
legal para ejercer los derechos ARCO) y el README. Se eliminó el teléfono placeholder
`+54 123 456 789` del footer, que era visible en producción.

El dominio `pielsanaia.click` venció y no se renueva: ya no queda ninguna referencia a él en el
código ni en la documentación.

### <a id="c8"></a>⚪ C8 · `console.log` en producción
- [x] Resuelto

`ImageUploader.tsx:171` y `:242`.

### <a id="c9"></a>⚪ C9 · Tres páginas de resultados prácticamente idénticas
- [x] Resuelto — `results/ResultadoLayout.tsx` lo comparten las **4** páginas (también `ResultsOpenAI`)

`ResultsLunares.tsx`, `ResultsAcne.tsx` y `ResultsRosacea.tsx` tienen **104 líneas cada una**;
el diff entre acné y rosácea es el ícono y el color. Un único componente
`<ResultadoAnalisis icono={} color={} />` elimina ~200 líneas y garantiza que un cambio en el
disclaimer médico se aplique a las tres.

### <a id="c10"></a>⚪ C10 · `<style>` inline duplicado
- [x] Resuelto — `.animate-fade-in` / `.animate-fade-in-slow` movidas a `index.css`

El mismo bloque `@keyframes fadeIn` está repetido en las 4 páginas de resultados, y `.fade-in`
ya existe en `index.css`.

### <a id="c11"></a>⚪ C11 · `hover:scale-102` no es una clase de Tailwind
- [x] Resuelto — `hover:scale-105`

`ImageUploader.tsx:247`. La escala de `scale` va 100/105/110 — esa clase no produce ningún
efecto.

### <a id="c12"></a>⚪ C12 · Regla CSS `.logo` sin sentido
- [x] Resuelto — regla `.logo` y `class="logo"` eliminadas

`index.css` define `.logo { width: 800px }`, y esa clase solo está aplicada al
`<link rel="icon" class="logo">` del `index.html`. Residuo, borrar ambos.

### <a id="c13"></a>⚪ C13 · Imágenes hotlinkeadas desde Pexels
- [x] Resuelto **parcialmente** — ahora hay una sola lista de URLs (`frontend/src/data/condiciones.ts`). **Pendiente:** descargarlas, pasarlas a WebP y servirlas desde `public/` con `width`/`height`

En `components/ConditionsOverview.tsx` y `backend/data/conditions.py` (el selector de tipos de
 análisis ya no las usa: el campo `image` se eliminó al mover el catálogo a `constants/analisis.ts`).
 El LCP del home
depende de un tercero, y si Pexels cambia las URLs se rompen las 4 tarjetas. Además van sin
`width`/`height` → *layout shift* (CLS). Descargar, optimizar a WebP y servirlas desde
`public/`.

---

## 4. SEO

Estado de partida: el `<head>` del `index.html` tiene **4 líneas**. Es el área con mayor
retorno por esfuerzo del proyecto.

### <a id="s1"></a>🔴 S1 · `<html lang="en">` con el sitio íntegramente en español
- [ ] Resuelto

`frontend/index.html:2`. Señal de idioma equivocada para Google. Cambiar a `lang="es"`
(o `es-AR`). Es literalmente un carácter.

### <a id="s2"></a>🔴 S2 · Sin `<meta name="description">`
- [ ] Resuelto

Google compone el snippet por su cuenta. Con una descripción propia se controla el CTR.

### <a id="s3"></a>🔴 S3 · Sin Open Graph ni Twitter Card
- [ ] Resuelto

Cuando alguien comparte el link **por WhatsApp** —que es como se va a difundir esta app— se ve
la URL pelada: sin título, sin descripción, sin imagen. Máximo impacto por mínimo esfuerzo.

Mínimo necesario: `og:title`, `og:description`, `og:image` (1200×630), `og:url`, `og:type`,
`og:locale=es_AR`, `twitter:card=summary_large_image`.

### <a id="s4"></a>🔴 S4 · Todo el contenido se renderiza en el cliente
- [ ] Resuelto

Los crawlers sociales (WhatsApp, Facebook, LinkedIn) **no ejecutan JavaScript**: aunque se
agreguen las etiquetas OG de [S3](#s3), en una SPA pura solo las ven si están en el HTML
estático. Googlebot sí renderiza JS, pero con retraso y peor posicionamiento.

Opciones, de menor a mayor esfuerzo:
1. Prerenderizar las rutas estáticas en el build (`vite-plugin-prerender` / `react-snap`).
2. Migrar el frontend a **Astro** (mantiene los componentes React y prerenderiza el resto).

Para el MVP alcanza con la opción 1 sobre las 6 rutas estáticas.

### <a id="s5"></a>🟡 S5 · Sin `robots.txt` ni `sitemap.xml`
- [ ] Resuelto

No hay ninguno en `frontend/public/`. Nada le indica a Google qué indexar. Importante además
marcar `noindex` en `/results`, `/results-acne`, `/results-rosacea` y `/results-openai`: no
aportan valor de búsqueda y son páginas con resultado personal.

### <a id="s6"></a>🟡 S6 · Sin datos estructurados (JSON-LD)
- [ ] Resuelto

Tres oportunidades concretas, con el contenido **ya escrito**:
- `FAQPage` sobre las 4 preguntas del FAQ de `About.tsx:112-142` → candidato directo a rich
  snippet en Google.
- `MedicalWebPage` en `/conditions/:condition`.
- `WebApplication` en el home.

### <a id="s7"></a>🟡 S7 · Un solo `<title>` para las 7 rutas
- [ ] Resuelto

Todas las páginas comparten título y descripción, así que Google las trata como duplicadas.
Solución barata sin dependencias nuevas: un hook `useDocumentTitle(titulo, descripcion)`
invocado desde cada página.

### <a id="s8"></a>🟡 S8 · Sin `<link rel="canonical">`
- [ ] Resuelto

Genera duplicados entre `www`/no-`www` y entre URLs con y sin barra final.

### <a id="s9"></a>🟡 S9 · `/conditions/:condition` depende de la API para renderizar
- [x] Resuelto — `conditions_data` movido a `frontend/src/data/condiciones.ts`; la página ya no llama al backend

Son las **mejores páginas SEO del proyecto** (contenido real y extenso sobre acné, rosácea,
lunares y manchas solares) y hoy son invisibles sin JS, además de depender de que el backend
esté vivo.

**Recomendación: mover `conditions_data` del backend al frontend como datos estáticos** y
prerenderizar esas rutas. Se gana SEO, velocidad y resiliencia de una sola vez. Se relaciona
con [A10](#a10).

### <a id="s10"></a>⚪ S10 · Sin `theme-color`, `apple-touch-icon` ni `manifest.json`
- [ ] Resuelto

Sin "agregar a pantalla de inicio" en móvil y sin color de barra en Android.

### <a id="s11"></a>⚪ S11 · Logos sin optimizar
- [ ] Resuelto

`public/logo.png` pesa **111 KB** y `public/logo1.png` **138 KB**. Un logo que se muestra a 32px
de alto no necesita 111 KB: WebP + resize lo dejan en ~5 KB. Verificar si `logo1.png` se usa —
no aparece referenciado en el código— y borrarlo si no.

### <a id="s12"></a>⚪ S12 · Bundle único de 218 KB sin code splitting
- [x] Resuelto — `React.lazy` en las 6 rutas no-home: bundle inicial 218 → 192 KB

`React.lazy` en las rutas de resultados baja el JS inicial del home y mejora el LCP.

---

## 5. Infraestructura, repo y procesos

### <a id="c14"></a>🟡 C14 · Assets con ruta absoluta: el logo rompe en subruta
- [x] Resuelto — `src={`${import.meta.env.BASE_URL}logo.png`}` en `Navbar` y `Footer`

`<img src="/logo.png">` en `Navbar.tsx:12` y `Footer.tsx:12`. Vite reescribe las rutas del
`index.html` con la `base`, pero **no** las cadenas dentro del JSX. Con
`VITE_BASE="/PielSanaIA-MVP/"` el ruteo funcionaba (ver [C3](#c3)) pero el logo daba **404**
en todas las páginas: [C3](#c3) estaba resuelto solo a medias.

Verificado con un build real: `VITE_BASE="/PielSanaIA-MVP/" npm run build` ahora emite
`/PielSanaIA-MVP/logo.png` en el bundle.

### <a id="c15"></a>⚪ C15 · CSS muerto en `index.css`
- [x] Resuelto — eliminados `@keyframes pulse` + `.pulse-animation` y `@keyframes slideIn` + `.slide-in`

Ninguna de las dos clases estaba aplicada en ningún componente. ~280 bytes de CSS que se
enviaban en cada carga.

### <a id="c16"></a>⚪ C16 · `color-scheme: light` con modo oscuro activo
- [x] Resuelto — `color-scheme: light dark`

`index.css` fijaba `color-scheme: light` mientras la app alterna `html.dark`. Los controles
nativos (scrollbar, inputs de archivo, selects) seguían renderizándose en claro sobre el tema
oscuro.

### <a id="c17"></a>⚪ C17 · Constante duplicada y componente fuera de su capa
- [x] Resuelto — `URL_TURNOS` a `constants/enlaces.ts`; `DarkModeToggle` a `components/ui/`

Residuos de la reestructuración: la URL de turnos quedó definida en `ResultadoLayout.tsx` **y**
en `ConditionsOverview.tsx`, y `DarkModeToggle.tsx` seguía suelto en la raíz de `src/` mientras
todo lo demás pasaba a capas.

### <a id="c18"></a>⚪ C18 · `vite-plugin-gh-pages` declarada y nunca importada
- [x] Resuelto — eliminada de `devDependencies`

No aparece en `vite.config.ts` ni en ningún otro archivo. **Ver [C19](#c19)**: el script
`npm run deploy` (gh-pages) sí sigue existiendo.

### <a id="c19"></a>🟡 C19 · El script de deploy contradice el plan de despliegue
- [ ] Resuelto

`package.json` mantiene `"deploy": "gh-pages -d dist"` y `CLAUDE.md` lo documenta, pero
`DESPLIEGUE.md` define **Vercel** como destino del frontend. Conviven dos caminos y solo uno es
el vigente. Decidir: si se va a Vercel, borrar el script y la dependencia `gh-pages`.

### <a id="c20"></a>⚪ C20 · El toggle de tema ignora `prefers-color-scheme` tras el primer render
- [ ] Resuelto

`DarkModeToggle` inicializa desde `prefers-color-scheme`, pero su `useEffect` escribe
`localStorage` en el montaje inicial. Desde ese momento la preferencia del sistema queda
congelada: si el usuario nunca tocó el botón y cambia el tema del SO, la app no acompaña.
Solo debería persistir ante una acción explícita del usuario.


### <a id="d1"></a>🟡 D1 · Sin `.dockerignore`
- [ ] Resuelto

El contexto de build incluye `frontend/node_modules/` y `frontend/dist/`: cientos de MB
enviados al daemon de Docker en cada `docker build`. Un `.dockerignore` de 5 líneas acelera
los builds drásticamente.

### <a id="d2"></a>🟡 D2 · El contenedor corre como root y arrastra `build-essential`
- [ ] Resuelto

`backend/Dockerfile:12` instala `build-essential` y nunca lo elimina → cientos de MB de más en
la imagen final y superficie de ataque innecesaria. Además no se define ningún usuario.
Solución: build multi-stage + `USER appuser`.

### <a id="d3"></a>🟡 D3 · Sin `HEALTHCHECK` en el Dockerfile
- [ ] Resuelto

Depende de resolver antes [A7](#a7) (no hay endpoint al cual apuntar).

### <a id="d4"></a>🟡 D4 · Sin integración continua
- [ ] Resuelto

Existe `backend/tests/test_api.py` con 9 tests y **nada los ejecuta automáticamente**. Un
workflow de GitHub Actions de ~20 líneas (`pytest` + `npm run lint` + `npm run build`) avisa
antes de romper producción.

### <a id="d5"></a>🟡 D5 · Huecos en la cobertura de tests
- [ ] Resuelto

No hay tests de: el endpoint de rosácea, el fallback de parseo JSON de los endpoints de IA
(que es justamente el camino que se ejecuta cuando el proveedor responde raro), ni la
configuración de CORS.

### <a id="d6"></a>⚪ D6 · Scripts de AWS obsoletos en la raíz
- [ ] Resuelto

`infra.sh`, `connect_aws.sh`, `nginx_manager.sh`, `reboot_backend.sh`, `dockerUbuntu.txt` y
`backend/datosusuarioUbuntu.txt` (este último, un duplicado casi idéntico de `dockerUbuntu.txt`).
Al migrar al VPS, mover a `infra/aws-legacy/` o eliminar.

> Contenido revisado en la auditoría: **no contienen secretos**, son solo scripts de instalación
> de Docker.

### <a id="d7"></a>⚪ D7 · `docker-compose.yml` y `nginx.conf` solo existen como texto
- [ ] Resuelto

Viven dentro de `DESPLIEGUE.md` como bloques para copiar al servidor. Conviene versionarlos
como archivos reales para que sean reproducibles y revisables.

### <a id="d8"></a>⚪ D8 · `README.md` desactualizado
- [ ] Resuelto

Ya se corrigieron: las instrucciones de despliegue con **EC2 + ngrok**, el arranque del backend
(`cd backend && python main.py`, que no funciona porque el paquete es `backend.main` desde la raíz),
el árbol del monorepo y la tabla de tecnologías (duplicaban `ARQUITECTURA.md`), el párrafo de
privacidad repetido, el *"Próximamente: rosácea y acné"* de modelos que ya existen y el contacto,
hoy unificado en [C7](#c7).

Queda pendiente: el README sigue diciendo que *"se recomienda agregar una política de privacidad
detallada"*, que es el mismo hueco de [C6](#c6).

> Sin números de línea a propósito: los anteriores quedaron desfasados al editar el README y
> mandaban a revisar cosas que ya no estaban.

### <a id="d9"></a>🔴 D9 · Datos biométricos de salud viajando en HTTP plano
- [ ] Resuelto

Hoy el backend responde por `http://54.82.199.243:8080`: las fotos de piel se transmiten **sin
cifrar**. Son datos sensibles de salud, y la app cita la Ley 25.326 en su propio modal de
consentimiento. Está registrado en `CLAUDE.md` como problema de *mixed content* (funcionalidad),
pero es además una falla de **confidencialidad**.

Se resuelve con el despliegue pendiente (DuckDNS + Let's Encrypt, sección 6).

---

## 6. Pendientes de despliegue (no son hallazgos de código)

Detalle completo en [`DESPLIEGUE.md`](DESPLIEGUE.md). Bloqueantes para tener el MVP online
(ver también [D9](#d9) — hoy el tráfico sensible va sin TLS):

- [ ] Contratar el VPS (Contabo o Hetzner, 2 vCPU / 4 GB) y levantar Docker Compose + Nginx + Let's Encrypt.
- [ ] Crear el subdominio **DuckDNS** → define `VITE_API_URL`.
- [ ] Desplegar el frontend en **Vercel** → su URL define `FRONTEND_ORIGINS` en el backend.
- [ ] Copiar los tres `.keras` al servidor (`backend/modelos/{ham10000,acne,rosacea}/`);
      hoy el repo solo tiene un `.gitkeep`.
- [ ] Crear el `.env` real en el servidor con `DEEPSEEK_API_KEY` (y opcionalmente
      `OPENAI_API_KEY`).

---

## Cosas que están bien

Para no perder de vista lo que ya funciona y no conviene tocar:

- Validación de subida sólida: tipo, tamaño por fragmentos de 64 KB (corta apenas supera los
  8 MB, sin bufferear la subida entera) y verificación de que la imagen sea decodificable.
- Backend **sin estado**: se eliminó el dict en memoria; los resultados viajan por
  `navigate(state)`.
- CORS configurable por entorno, ya no `allow_origins=["*"]`.
- Sin secretos en el código ni en los scripts versionados; los `print` de API keys se
  eliminaron.
- Manejo de errores de los proveedores de IA centralizado y con códigos correctos (502/503).
- Deduplicación ya hecha en `analizar_con_modelo()`, `_preprocesar_imagen()` y
  `_completar_chat()`.
- Modo oscuro coherente en toda la app y `aria-label` correcto en el toggle.
- Tono clínico consistente: el disclaimer de "no sustituye a un dermatólogo" aparece en las 4
  páginas de resultados y en las de condiciones.
- Plantillas `.env.example` documentadas en la raíz y en `frontend/`.
- **Sin secretos versionados:** `git ls-files` solo devuelve los dos `.env.example`; ningún `.env`,
  `.pem` ni `.keras`. El `.gitignore` cubre `.env` en cualquier nivel, `*.pem`, `*.exe` y `*.bak`.
- **Dependencias del frontend limpias:** `npm audit --omit=dev` → 0 vulnerabilidades.
- `Pillow==11.1.0` arrastra CVE-2025-48379, pero **no aplica**: es en la *escritura* de archivos
  DDS y el proyecto solo lee imágenes. Conviene subir a 11.3+ igual, sin urgencia.
