import React, { useState } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import { TIPOS_ANALISIS, type ClaveAnalisis } from '../../constants/analisis';
import { useAnalisisImagen } from '../../hooks/useAnalisisImagen';
import BannerError from '../ui/BannerError';
import ConsentModal from './ConsentModal';
import SelectorTipoAnalisis from './SelectorTipoAnalisis';
import VistaPreviaImagen from './VistaPreviaImagen';
import ZonaDeSubida from './ZonaDeSubida';

/**
 * Orquesta el flujo de análisis: elegir tipo → consentir → subir imagen → analizar.
 *
 * Solo compone; el estado vive en `useAnalisisImagen` y cada paso es su propio
 * componente. Antes esto era un único archivo de 343 líneas.
 */
const ImageUploader: React.FC = () => {
  const [tipoElegido, setTipoElegido] = useState<ClaveAnalisis | null>(null);
  const [mostrarConsentimiento, setMostrarConsentimiento] = useState(false);
  const [consentimientoAceptado, setConsentimientoAceptado] = useState(false);
  const { vistaPrevia, analizando, error, setError, seleccionarArchivo, limpiar, analizar } =
    useAnalisisImagen();

  const tipo = TIPOS_ANALISIS.find(t => t.clave === tipoElegido) ?? null;
  const puedeSubir = Boolean(tipo) && consentimientoAceptado;

  // Cambiar de tipo de análisis vuelve a pedir el consentimiento y descarta la imagen:
  // el consentimiento es específico del tratamiento que se va a hacer.
  const elegirTipo = (clave: ClaveAnalisis) => {
    setTipoElegido(clave);
    setConsentimientoAceptado(false);
    setMostrarConsentimiento(true);
    limpiar();
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-xl shadow-md">
      {mostrarConsentimiento && (
        <ConsentModal
          onAccept={() => {
            setMostrarConsentimiento(false);
            setConsentimientoAceptado(true);
          }}
          onClose={() => {
            setMostrarConsentimiento(false);
            setConsentimientoAceptado(false);
          }}
        />
      )}

      <div className="flex items-center text-blue-600 mb-4 justify-center">
        <ImageIcon className="h-6 w-6 mr-2" />
        <h2 className="text-xl font-semibold text-center">Análisis de Imagen</h2>
      </div>

      {error && <BannerError mensaje={error} onCerrar={() => setError(null)} />}

      {!vistaPrevia && (
        <SelectorTipoAnalisis seleccionado={tipoElegido} onSeleccionar={elegirTipo} />
      )}

      {vistaPrevia ? (
        <VistaPreviaImagen
          src={vistaPrevia}
          analizando={analizando}
          onQuitar={limpiar}
          onAnalizar={() => tipo && analizar(tipo)}
        />
      ) : (
        <ZonaDeSubida habilitada={puedeSubir} onArchivo={seleccionarArchivo} />
      )}
    </div>
  );
};

export default ImageUploader;
