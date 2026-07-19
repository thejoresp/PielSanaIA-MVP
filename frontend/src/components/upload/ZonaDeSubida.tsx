import React, { useRef, useState } from 'react';
import { Camera, Upload } from 'lucide-react';

interface Props {
  /** Mientras sea false no se acepta ningún archivo (falta elegir tipo o dar consentimiento). */
  habilitada: boolean;
  onArchivo: (file: File) => void;
}

/** Zona de arrastrar-y-soltar + botón de selección. */
const ZonaDeSubida: React.FC<Props> = ({ habilitada, onArchivo }) => {
  const [arrastrando, setArrastrando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const tomarPrimero = (archivos: FileList | null) => {
    if (archivos?.[0]) onArchivo(archivos[0]);
  };

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors duration-200 ${
        arrastrando ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/30' : 'border-gray-300'
      }`}
      onDragOver={e => {
        if (!habilitada) return;
        e.preventDefault();
        setArrastrando(true);
      }}
      onDragLeave={() => setArrastrando(false)}
      onDrop={e => {
        if (!habilitada) return;
        e.preventDefault();
        setArrastrando(false);
        tomarPrimero(e.dataTransfer.files);
      }}
    >
      <Upload className="mx-auto h-12 w-12 text-gray-400" />
      <p className="mt-2 text-lg font-medium text-gray-900 dark:text-gray-100">
        Sube una foto de tu piel
      </p>
      <p className="text-sm text-gray-500 dark:text-gray-300 mt-1">
        Arrastra y suelta o haz clic para seleccionar
      </p>

      <div className="mt-6">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          ref={inputRef}
          disabled={!habilitada}
          onChange={e => tomarPrimero(e.target.files)}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={!habilitada}
          className={`inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white ${
            habilitada
              ? 'bg-blue-600 hover:bg-blue-700'
              : 'bg-gray-300 dark:bg-gray-700 cursor-not-allowed'
          } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
        >
          <Camera className="h-5 w-5 mr-2" />
          Seleccionar Imagen
        </button>
      </div>
    </div>
  );
};

export default ZonaDeSubida;
