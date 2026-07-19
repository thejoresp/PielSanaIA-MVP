/** Endpoints del backend, tipados. Los componentes llaman a esto, nunca a `fetch`. */
import { apiPostArchivo, apiPostJson } from './client';
import type { AnalisisResultado, Recomendaciones, VisionResultado } from '../types/skin';

/**
 * Ejecuta un análisis de imagen.
 *
 * El `endpoint` lo define el catálogo de `constants/analisis.ts`, así que agregar un
 * tipo de análisis no requiere tocar esta función.
 */
export const analizarImagen = (endpoint: string, file: File) =>
  apiPostArchivo<AnalisisResultado | VisionResultado>(endpoint, file);

/** Descripción y recomendaciones para una predicción de los modelos locales. */
export const obtenerRecomendaciones = (prediccion: string) =>
  apiPostJson<Recomendaciones>('/skin/openai-recomendaciones', { prediccion });
