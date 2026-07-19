/**
 * Cliente HTTP del backend.
 *
 * Concentra acá la URL base, el manejo de errores y la lectura del `detail` que
 * devuelve FastAPI. Antes cada componente hacía su propio `fetch` y descartaba el
 * mensaje del servidor a favor de un `alert()` genérico.
 */

const API_URL = import.meta.env.VITE_API_URL;

// `VITE_API_URL` se resuelve en build time. Si falta, las peticiones irían a
// `undefined/skin/...` y fallarían en silencio; el aviso explícito ahorra horas de
// debugging después de un deploy.
if (!API_URL) {
  console.error(
    '[PielSana IA] Falta VITE_API_URL. Definila en frontend/.env ANTES de `npm run build`, ' +
      'si no todas las llamadas al backend van a fallar.',
  );
}

/** Error de la API con el código HTTP y un mensaje ya listo para mostrar al usuario. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** Mensajes por defecto cuando el backend no manda un `detail` aprovechable. */
const MENSAJES_POR_ESTADO: Record<number, string> = {
  0: 'No pudimos conectarnos con el servidor. Revisá tu conexión e intentá de nuevo.',
  413: 'La imagen es demasiado grande. Probá con una foto de menos de 8 MB.',
  422: 'El dato enviado no es válido. Volvé a realizar el análisis.',
  429: 'Hiciste demasiadas consultas seguidas. Esperá un minuto y volvé a intentar.',
  502: 'El servicio de análisis no está respondiendo. Intentá nuevamente en unos minutos.',
  503: 'El análisis con IA no está disponible en este momento.',
};

async function leerMensajeDeError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data?.detail === 'string') return data.detail;
  } catch {
    // El cuerpo no era JSON: se usa el mensaje por estado.
  }
  return MENSAJES_POR_ESTADO[response.status] ?? 'Ocurrió un error inesperado. Intentá nuevamente.';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    // Falla de red / CORS / backend caído: nunca llegamos a tener un status.
    throw new ApiError(0, MENSAJES_POR_ESTADO[0]);
  }

  if (!response.ok) {
    throw new ApiError(response.status, await leerMensajeDeError(response));
  }
  return response.json() as Promise<T>;
}

export const apiPostJson = <T>(path: string, body: unknown) =>
  request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

export const apiPostArchivo = <T>(path: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return request<T>(path, { method: 'POST', body: formData });
};
