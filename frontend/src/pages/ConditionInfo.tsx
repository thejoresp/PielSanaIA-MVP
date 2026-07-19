import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Check, Zap, ShieldCheck, Info } from 'lucide-react';
import { buscarCondicion } from '../data/condiciones';

/**
 * Ficha educativa de una condición cutánea.
 *
 * Lee de `data/condiciones.ts`: **no depende del backend**. Antes hacía un fetch a
 * `/skin/api/condition/{nombre}` y la página quedaba vacía si el backend no respondía,
 * pese a ser contenido estático.
 */

/** Lista con ítems numerados (causas). */
const ListaNumerada: React.FC<{ items: string[] }> = ({ items }) => (
  <ul className="space-y-2">
    {items.map((item, i) => (
      <li key={i} className="flex items-start">
        <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 text-blue-800 text-sm font-medium mr-3 flex-shrink-0">
          {i + 1}
        </span>
        <span className="text-gray-600 dark:text-gray-300">{item}</span>
      </li>
    ))}
  </ul>
);

/** Lista con un ícono por ítem, reutilizada por síntomas, tratamiento y prevención. */
const ListaConIcono: React.FC<{
  items: string[];
  icono: React.ElementType;
  colorIcono: string;
  colorTexto?: string;
}> = ({ items, icono: Icono, colorIcono, colorTexto = 'text-gray-600 dark:text-gray-300' }) => (
  <ul className="space-y-2">
    {items.map((item, i) => (
      <li key={i} className="flex items-start">
        <Icono className={`h-5 w-5 mr-3 flex-shrink-0 ${colorIcono}`} />
        <span className={colorTexto}>{item}</span>
      </li>
    ))}
  </ul>
);

const ConditionInfo: React.FC = () => {
  const { condition } = useParams<{ condition: string }>();
  const data = buscarCondicion(condition);

  if (!data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8 text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Condición no encontrada
        </h2>
        <p className="mt-2 text-gray-600 dark:text-gray-300">
          La información sobre esta condición no está disponible.
        </p>
        <Link to="/" className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-800">
          <ArrowLeft className="h-5 w-5 mr-1" />
          Volver al inicio
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <Link to="/" className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-6">
        <ArrowLeft className="h-5 w-5 mr-1" />
        Volver al inicio
      </Link>

      <article className="bg-white shadow-md rounded-lg overflow-hidden">
        <div className="h-64 overflow-hidden">
          <img src={data.imagen} alt={data.titulo} className="w-full h-full object-cover" />
        </div>

        <div className="p-6 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">{data.titulo}</h1>
          <p className="text-lg text-gray-700 dark:text-gray-300 mb-8">{data.descripcion}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <section>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Causas</h2>
              <ListaNumerada items={data.causas} />
            </section>
            <section>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Síntomas
              </h2>
              <ListaConIcono items={data.sintomas} icono={Check} colorIcono="text-blue-600" />
            </section>
          </div>

          <section className="mt-8">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Tratamiento
            </h2>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-100 dark:border-blue-700 mb-6">
              <ListaConIcono
                items={data.tratamiento}
                icono={Zap}
                colorIcono="text-blue-600 dark:text-blue-400"
                colorTexto="text-gray-700 dark:text-gray-200"
              />
            </div>

            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Prevención
            </h2>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-100 dark:border-green-700">
              <ListaConIcono
                items={data.prevencion}
                icono={ShieldCheck}
                colorIcono="text-green-600 dark:text-green-400"
                colorTexto="text-gray-700 dark:text-gray-200"
              />
            </div>
          </section>

          <aside className="mt-10 p-6 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center mb-4">
              <Info className="h-6 w-6 text-yellow-500 mr-3" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Importante</h3>
            </div>
            <p className="text-gray-600 dark:text-gray-300">
              La información proporcionada es de carácter general y educativo. Siempre consulta con
              un dermatólogo profesional para un diagnóstico preciso y un plan de tratamiento
              personalizado.
            </p>
          </aside>
        </div>
      </article>
    </div>
  );
};

export default ConditionInfo;
