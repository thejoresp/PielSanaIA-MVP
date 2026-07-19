import React from 'react';
import { useLocation } from 'react-router-dom';
import { AlertCircle, Thermometer, Sun, Crosshair } from 'lucide-react';
import ResultadoLayout, { type TemaResultado } from '../components/results/ResultadoLayout';
import SinResultado from '../components/results/SinResultado';
import type { VisionResultado } from '../types/skin';

/**
 * Resultados del análisis por visión (`/skin/openai-analizar`).
 *
 * A diferencia de los modelos locales, acá la afección la nombra el propio modelo en
 * texto libre: puede no coincidir con ninguna de las conocidas, y en ese caso se cae a
 * una presentación genérica.
 */

interface Presentacion {
  icono: React.ReactNode;
  tema: TemaResultado;
  descripcionPorDefecto: string;
}

const AFECCIONES_CONOCIDAS: Record<string, Presentacion> = {
  'acné': {
    icono: <AlertCircle className="h-10 w-10 text-pink-500" />,
    tema: 'rosa',
    descripcionPorDefecto:
      'El acné es una condición común causada por la obstrucción de los folículos pilosos con grasa y células muertas.',
  },
  'rosácea': {
    icono: <Thermometer className="h-10 w-10 text-red-500" />,
    tema: 'rojo',
    descripcionPorDefecto:
      'La rosácea es una afección crónica que causa enrojecimiento y vasos sanguíneos visibles en la cara.',
  },
  'mancha solar': {
    icono: <Sun className="h-10 w-10 text-yellow-500" />,
    tema: 'amarillo',
    descripcionPorDefecto:
      'Las manchas solares son áreas de la piel que se oscurecen debido a la exposición al sol.',
  },
  'lunares': {
    icono: <Crosshair className="h-10 w-10 text-blue-500" />,
    tema: 'azul',
    descripcionPorDefecto:
      'Los lunares son áreas pequeñas de pigmentación en la piel. La mayoría son inofensivos, pero es importante monitorearlos.',
  },
};

const ResultsOpenAI: React.FC = () => {
  const location = useLocation();
  const analysis = location.state?.analysis as VisionResultado | undefined;

  if (!analysis) return <SinResultado />;

  const conocida = AFECCIONES_CONOCIDAS[analysis.afeccion?.toLowerCase() ?? ''];

  return (
    <ResultadoLayout
      titulo={
        analysis.afeccion
          ? `Afección detectada: ${analysis.afeccion}`
          : 'Resultados del Análisis de Piel (IA Avanzada)'
      }
      tema={conocida?.tema ?? 'azul'}
      icono={conocida?.icono}
      subtitulo={
        conocida
          ? undefined
          : 'Este resultado es orientativo y no reemplaza la opinión de un profesional.'
      }
      descripcion={analysis.descripcion ?? conocida?.descripcionPorDefecto}
      recomendaciones={analysis.recomendaciones}
    />
  );
};

export default ResultsOpenAI;
