import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface Props {
  mensaje: string;
  onCerrar?: () => void;
}

/**
 * Banner de error dentro de la UI.
 *
 * Reemplaza a los `alert()`, que bloqueaban la página y descartaban el `detail` que
 * manda el backend (tamaño excedido, rate limit, IA sin configurar).
 */
const BannerError: React.FC<Props> = ({ mensaje, onCerrar }) => (
  <div
    role="alert"
    className="mb-4 flex items-start gap-3 rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-700 dark:bg-red-900/40"
  >
    <AlertTriangle className="h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-300 mt-0.5" />
    <p className="flex-1 text-sm font-medium text-red-800 dark:text-red-100">{mensaje}</p>
    {onCerrar && (
      <button
        type="button"
        onClick={onCerrar}
        aria-label="Cerrar aviso"
        className="text-red-600 hover:text-red-800 dark:text-red-300 dark:hover:text-red-100"
      >
        <X className="h-4 w-4" />
      </button>
    )}
  </div>
);

export default BannerError;
