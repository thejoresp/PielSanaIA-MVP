import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { obtenerRecomendaciones } from '../../api/skin';
import type { AnalisisResultado } from '../../types/skin';
import ResultadoLayout, { type TemaResultado } from './ResultadoLayout';
import SinResultado from './SinResultado';

/**
 * Página de resultados de los modelos locales (lunares, acné, rosácea).
 *
 * Toma la predicción del `navigate(state)` y le pide a la IA la descripción y las
 * recomendaciones. Las tres páginas eran archivos idénticos de 104 líneas salvo por el
 * ícono y el color.
 */

interface Props {
  icono: LucideIcon;
  tema: TemaResultado;
  /** Clase de color del ícono (Tailwind completa, no interpolada). */
  colorIcono: string;
}

const ResultadoModeloLocal: React.FC<Props> = ({ icono: Icono, tema, colorIcono }) => {
  const location = useLocation();
  const analysis = location.state?.analysis as AnalisisResultado | undefined;
  const [descripcion, setDescripcion] = useState('');
  const [recomendaciones, setRecomendaciones] = useState<string[]>([]);

  const prediccion = analysis?.prediccion;

  useEffect(() => {
    if (!prediccion) return;

    let cancelado = false;
    obtenerRecomendaciones(prediccion)
      .then(data => {
        // Evita el setState si el usuario navegó antes de que respondiera.
        if (cancelado) return;
        setDescripcion(data.descripcion ?? '');
        setRecomendaciones(data.recomendaciones ?? []);
      })
      .catch(() => {
        // Si la IA falla, la página sigue mostrando la predicción del modelo local.
        if (cancelado) return;
        setDescripcion('');
        setRecomendaciones([]);
      });

    return () => {
      cancelado = true;
    };
  }, [prediccion]);

  if (!analysis) return <SinResultado />;

  return (
    <ResultadoLayout
      titulo={`Afección detectada: ${analysis.prediccion}`}
      tema={tema}
      icono={<Icono className={`h-10 w-10 ${colorIcono}`} />}
      descripcion={descripcion}
      recomendaciones={recomendaciones}
    />
  );
};

export default ResultadoModeloLocal;
