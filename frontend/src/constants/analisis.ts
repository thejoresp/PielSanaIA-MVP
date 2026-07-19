/**
 * Catálogo de tipos de análisis.
 *
 * Cada entrada declara su endpoint y su ruta de resultados. Antes esto vivía como una
 * cadena de `if/else` más tres booleanos paralelos (`isAcne`, `isRosacea`, `isOpenAI`)
 * dentro de `ImageUploader`; sumar un modelo obligaba a tocar tres lugares.
 *
 * Para agregar un análisis nuevo: una entrada acá + su ruta en `App.tsx`.
 */

export type ClaveAnalisis = 'acne' | 'rosacea' | 'lunares' | 'vision';

export interface TipoAnalisis {
  clave: ClaveAnalisis;
  etiqueta: string;
  descripcion: string;
  /** Path del backend, sin la URL base. */
  endpoint: string;
  /** Ruta del frontend a la que se navega con el resultado. */
  ruta: string;
}

export const TIPOS_ANALISIS: TipoAnalisis[] = [
  {
    clave: 'acne',
    etiqueta: 'Acné',
    descripcion: 'Detección y análisis de lesiones acneicas.',
    endpoint: '/skin/api/analyze-acne',
    ruta: '/results-acne',
  },
  {
    clave: 'rosacea',
    etiqueta: 'Rosácea',
    descripcion: 'Identificación de enrojecimiento y vasos sanguíneos.',
    endpoint: '/skin/api/analyze-rosacea',
    ruta: '/results-rosacea',
  },
  {
    clave: 'lunares',
    etiqueta: 'Lunares',
    descripcion: 'Análisis de lunares y lesiones atípicas.',
    endpoint: '/skin/api/analyze-lunares',
    ruta: '/results',
  },
  {
    clave: 'vision',
    etiqueta: 'Detectar Condición',
    descripcion:
      'Analiza tu imagen con IA avanzada y detecta automáticamente el tipo de problema de piel.',
    endpoint: '/skin/openai-analizar',
    ruta: '/results-openai',
  },
];
