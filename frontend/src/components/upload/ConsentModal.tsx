import React, { useState } from 'react';

/**
 * Consentimiento informado (Ley N.º 25.326) previo al análisis.
 *
 * ⚠️ El texto y el correo de contacto tienen valor legal: es el canal por el que se
 * ejercen los derechos ARCO. No cambiarlos sin revisar `docs/AUDITORIA.md` (C6, C7).
 */

const CONTACTO_DATOS = 'thejoresp@gmail.com';

interface Props {
  onAccept: () => void;
  onClose: () => void;
}

const ConsentModal: React.FC<Props> = ({ onAccept, onClose }) => {
  const [aceptado, setAceptado] = useState(false);

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
    >
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 id="consent-title" className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
            Consentimiento
          </h2>
          <div className="prose prose-sm dark:text-gray-200">
            <h3 className="text-lg font-semibold mb-2">
              📄 Consentimiento Informado para el Tratamiento de Datos Faciales
            </h3>
            <p>
              Piel Sana IA te informa que, para poder analizar tu imagen, necesitamos tu
              consentimiento para el tratamiento de datos personales sensibles, conforme a la Ley
              N.º 25.326 de Protección de Datos Personales y normativa aplicable.
            </p>

            <h4 className="font-semibold mt-4 mb-2">¿Para qué se usan tus datos?</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>Promover el bienestar, autocuidado y prevención de problemas dermatológicos.</li>
              <li>
                Brindar información orientativa sobre el estado de tu piel y posibles condiciones
                frecuentes.
              </li>
              <li>
                Facilitar el acceso a herramientas de salud para todas las personas, sin distinción.
              </li>
            </ul>

            <h4 className="font-semibold mt-4 mb-2">¿Qué datos se procesan?</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>Imágenes faciales que subas para el análisis.</li>
              <li>Datos derivados de la imagen (resultados automáticos del análisis).</li>
            </ul>

            <h4 className="font-semibold mt-4 mb-2">Privacidad y Seguridad</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>Tus imágenes se procesan solo para el análisis y se eliminan inmediatamente después.</li>
              <li>No se almacenan datos personales ni se comparten con terceros.</li>
              <li>Se aplican medidas de seguridad para proteger tu información.</li>
            </ul>

            <h4 className="font-semibold mt-4 mb-2">Tus derechos</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                Puedes solicitar acceso, rectificación, actualización, cancelación u oposición al
                tratamiento de tus datos escribiendo a{' '}
                <a href={`mailto:${CONTACTO_DATOS}`}>{CONTACTO_DATOS}</a>.
              </li>
            </ul>

            <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
              <p className="font-medium text-gray-700 dark:text-gray-200">
                Al aceptar, confirmas que has leído y comprendido la información anterior, y prestas
                tu consentimiento libre, expreso e informado para el tratamiento temporal de tus
                datos sensibles en los términos expuestos.
              </p>
            </div>
          </div>

          <div className="mt-6 flex items-center">
            <input
              id="consent-check"
              type="checkbox"
              checked={aceptado}
              onChange={e => setAceptado(e.target.checked)}
              className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label
              htmlFor="consent-check"
              className="text-gray-800 dark:text-gray-200 text-sm select-none"
            >
              He leído y acepto el consentimiento informado para el tratamiento de mis datos
              sensibles.
            </label>
          </div>

          <div className="mt-6 flex justify-end space-x-4">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
            >
              Cancelar
            </button>
            <button
              onClick={onAccept}
              disabled={!aceptado}
              className={`px-4 py-2 rounded-md text-white ${
                aceptado
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-gray-400 dark:bg-gray-600 cursor-not-allowed'
              }`}
            >
              Aceptar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConsentModal;
