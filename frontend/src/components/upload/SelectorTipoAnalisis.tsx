import React from 'react';
import { CheckCircle } from 'lucide-react';
import { TIPOS_ANALISIS, type ClaveAnalisis } from '../../constants/analisis';

interface Props {
  seleccionado: ClaveAnalisis | null;
  onSeleccionar: (clave: ClaveAnalisis) => void;
}

/** Grilla de tarjetas para elegir qué modelo se va a usar. */
const SelectorTipoAnalisis: React.FC<Props> = ({ seleccionado, onSeleccionar }) => (
  <div className="mb-6">
    <h3 className="text-lg font-medium mb-3 text-gray-800 dark:text-gray-100 text-center">
      Selecciona el tipo de análisis que deseas realizar
    </h3>
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
      {TIPOS_ANALISIS.map(tipo => {
        const activo = seleccionado === tipo.clave;
        return (
          <button
            key={tipo.clave}
            type="button"
            onClick={() => onSeleccionar(tipo.clave)}
            aria-pressed={activo}
            className={`relative flex flex-col items-start h-full bg-white dark:bg-gray-800 border rounded-xl shadow-sm transition-all duration-300 ease-in-out overflow-hidden text-left
              ${
                activo
                  ? 'border-blue-500 ring-2 ring-blue-400 shadow-xl scale-105'
                  : 'border-gray-200 hover:border-blue-300 hover:shadow-lg hover:scale-105'
              }
              focus:outline-none focus:ring-2 focus:ring-blue-300`}
          >
            {activo && (
              <span className="absolute top-2 right-2 z-10 text-blue-500">
                <CheckCircle className="h-6 w-6" />
              </span>
            )}
            <div className="p-6 flex-1 flex flex-col w-full">
              <span className="text-blue-700 dark:text-blue-300 font-semibold text-lg mb-1">
                {tipo.etiqueta}
              </span>
              <span className="text-gray-600 dark:text-gray-300 text-sm mb-2 flex-1">
                {tipo.descripcion}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  </div>
);

export default SelectorTipoAnalisis;
