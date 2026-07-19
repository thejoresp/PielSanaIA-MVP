import React from 'react';
import { X } from 'lucide-react';
import Spinner from '../ui/Spinner';

interface Props {
  src: string;
  analizando: boolean;
  onQuitar: () => void;
  onAnalizar: () => void;
}

/** Vista previa de la imagen elegida, con el botón para lanzar el análisis. */
const VistaPreviaImagen: React.FC<Props> = ({ src, analizando, onQuitar, onAnalizar }) => (
  <div className="space-y-4">
    <div className="relative">
      <img src={src} alt="Imagen para análisis" className="mx-auto max-h-80 rounded-lg object-contain" />
      <button
        type="button"
        onClick={onQuitar}
        title="Eliminar imagen"
        aria-label="Eliminar imagen"
        className="absolute top-2 right-2 flex items-center justify-center w-10 h-10 bg-gray-200 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-full shadow hover:bg-red-600 hover:text-white hover:border-red-600 transition-colors focus:outline-none"
      >
        <X className="h-6 w-6" />
      </button>
    </div>

    <div className="flex justify-center">
      <button
        type="button"
        onClick={onAnalizar}
        disabled={analizando}
        className={`inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white ${
          analizando ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'
        } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200`}
      >
        {analizando ? (
          <>
            <Spinner />
            Analizando...
          </>
        ) : (
          'Analizar Imagen'
        )}
      </button>
    </div>
  </div>
);

export default VistaPreviaImagen;
