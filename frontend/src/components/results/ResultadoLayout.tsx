import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, CheckCircle } from 'lucide-react';
import { URL_TURNOS } from '../../constants/enlaces';

/**
 * Carcasa visual de TODAS las páginas de resultados (los tres modelos locales y el de
 * visión). Es puramente presentacional: no hace peticiones ni conoce el origen del dato.
 *
 * El disclaimer médico vive acá una sola vez: al editarlo, cambia en las cuatro páginas.
 */

export type TemaResultado = 'azul' | 'rosa' | 'rojo' | 'amarillo';

/**
 * Clases Tailwind completas por tema. No se pueden armar por interpolación
 * (`bg-${color}-100`): el purge del build las descarta y el panel queda sin estilo.
 */
const TEMAS: Record<TemaResultado, { panel: string; texto: string }> = {
  azul: {
    panel: 'bg-blue-100 dark:bg-blue-900/80 border-blue-300 dark:border-blue-600',
    texto: 'text-gray-700 dark:text-blue-100',
  },
  rosa: {
    panel: 'bg-pink-100 dark:bg-pink-900/80 border-pink-300 dark:border-pink-600',
    texto: 'text-gray-700 dark:text-pink-100',
  },
  rojo: {
    panel: 'bg-red-100 dark:bg-red-900/80 border-red-300 dark:border-red-600',
    texto: 'text-gray-700 dark:text-red-100',
  },
  amarillo: {
    panel: 'bg-yellow-100 dark:bg-yellow-900/80 border-yellow-300 dark:border-yellow-600',
    texto: 'text-gray-700 dark:text-yellow-100',
  },
};

interface Props {
  titulo: string;
  tema: TemaResultado;
  /** Ícono ya renderizado; opcional porque el flujo de visión puede no reconocer la afección. */
  icono?: React.ReactNode;
  /** Aclaración bajo el título (p. ej. cuando la afección detectada no se reconoce). */
  subtitulo?: string;
  descripcion?: string;
  recomendaciones?: string[];
}

const ResultadoLayout: React.FC<Props> = ({
  titulo,
  tema,
  icono,
  subtitulo,
  descripcion,
  recomendaciones = [],
}) => {
  const estilos = TEMAS[tema];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 fade-in">
      <Link to="/" className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-6">
        <ArrowLeft className="h-5 w-5 mr-1" />
        Volver al inicio
      </Link>

      <div className="bg-white dark:bg-gray-900 shadow rounded-lg overflow-hidden">
        <header className="bg-blue-600 dark:bg-blue-700 py-6 px-6 rounded-t-lg shadow-xl border-2 border-blue-400 dark:border-blue-700">
          <div className="flex items-center space-x-4">
            {icono}
            <h1 className="text-3xl font-bold text-white animate-fade-in">{titulo}</h1>
          </div>
          {subtitulo && <p className="text-blue-100 mt-2">{subtitulo}</p>}
        </header>

        <div className="p-6 bg-gray-50 dark:bg-gray-800">
          {descripcion && (
            <section className={`mb-6 rounded-lg p-6 border shadow-lg animate-fade-in ${estilos.panel}`}>
              <p className={`text-base ${estilos.texto}`}>{descripcion}</p>
            </section>
          )}

          {recomendaciones.length > 0 && (
            <section className="mb-8">
              <h2 className="text-lg font-semibold mb-4 text-blue-800 dark:text-blue-300">
                Recomendaciones
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                {recomendaciones.map((rec, idx) => (
                  <div
                    key={idx}
                    className="flex items-start bg-green-50 dark:bg-green-900 border-l-4 border-green-400 dark:border-green-500 rounded-lg p-4 shadow-sm animate-fade-in"
                  >
                    <CheckCircle className="h-6 w-6 text-green-500 dark:text-green-300 mr-3 mt-1" />
                    <span className="text-gray-800 dark:text-green-100 text-base">{rec}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Disclaimer médico: PielSana IA es una herramienta educativa, no diagnóstica. */}
          <div className="flex items-start space-x-2 mb-6 animate-fade-in-slow">
            <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <p className="text-yellow-900 bg-yellow-100 rounded px-3 py-2 text-sm font-medium">
              <span className="font-medium">Nota importante:</span> Este análisis es preliminar y no
              constituye un diagnóstico médico. Siempre consulta con un dermatólogo para una
              evaluación profesional.
            </p>
          </div>

          <section className="bg-blue-50 dark:bg-blue-800 border border-blue-200 dark:border-blue-700 rounded-lg p-6 mb-6 animate-fade-in-slow">
            <h3 className="text-xl font-semibold text-blue-800 dark:text-blue-100 mb-3">
              Próximos Pasos
            </h3>
            <p className="text-gray-700 dark:text-blue-100 mb-4">
              Para un diagnóstico preciso y un plan de tratamiento personalizado, te recomendamos
              consultar con un dermatólogo. Tu salud dermatológica es importante.
            </p>
            <button
              type="button"
              onClick={() => window.open(URL_TURNOS, '_blank', 'noopener,noreferrer')}
              className="bg-blue-600 text-white px-8 py-3 rounded-md hover:bg-blue-700 transition-colors text-lg font-semibold shadow"
            >
              Encontrar Especialista
            </button>
          </section>

          <div className="text-center">
            <Link
              to="/"
              className="text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-400 font-medium"
            >
              Realizar nuevo análisis
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultadoLayout;
