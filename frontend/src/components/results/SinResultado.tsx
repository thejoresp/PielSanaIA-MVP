import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Estado vacío de las páginas de resultados.
 *
 * Se llega acá al entrar por URL directa o al recargar: el resultado viaja por
 * `navigate(state)` y no sobrevive al refresh (el backend es sin estado a propósito).
 */
const SinResultado: React.FC = () => (
  <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8 text-center">
    <h2 className="text-xl font-bold mb-2 text-gray-900 dark:text-gray-100">
      No hay resultado disponible
    </h2>
    <p className="mb-4 text-gray-600 dark:text-gray-300">
      Los resultados no se guardan: volvé al inicio y realizá el análisis nuevamente.
    </p>
    <Link to="/" className="text-blue-600 hover:text-blue-800 font-medium">
      Volver al inicio
    </Link>
  </div>
);

export default SinResultado;
