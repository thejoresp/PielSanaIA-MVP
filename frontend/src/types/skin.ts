/** Formas de los datos que devuelve el backend. Una sola fuente de verdad. */

/** Respuesta de los endpoints de modelo local (`/skin/api/analyze-*`). */
export interface AnalisisResultado {
  filename: string;
  content_type: string;
  /** Etiqueta legible en español, p. ej. "Melanoma" o "Con acné". */
  prediccion: string;
  /** Probabilidad por etiqueta. Hoy el frontend no la muestra (ver B4 en AUDITORIA.md). */
  probabilidades: Record<string, number>;
}

/** Respuesta del endpoint de visión (`/skin/openai-analizar`). */
export interface VisionResultado {
  afeccion?: string;
  descripcion?: string;
  recomendaciones?: string[];
}

/** Respuesta de `/skin/openai-recomendaciones`. */
export interface Recomendaciones {
  descripcion?: string;
  recomendaciones?: string[];
}
