import React from 'react';

/**
 * Red de contención para excepciones durante el render.
 *
 * Sin esto, cualquier error en un componente deja la pantalla en blanco, sin mensaje
 * ni forma de volver — y en producción ni siquiera se ve el stack.
 *
 * Tiene que ser una clase: React no expone equivalente en hooks.
 */
interface Props {
  children: React.ReactNode;
}

interface State {
  huboError: boolean;
}

class ErrorBoundary extends React.Component<Props, State> {
  state: State = { huboError: false };

  static getDerivedStateFromError(): State {
    return { huboError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[PielSana IA] Error no controlado en el render:', error, info.componentStack);
  }

  render() {
    if (!this.state.huboError) return this.props.children;

    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Algo salió mal
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mb-6">
          Ocurrió un error inesperado. Podés recargar la página e intentar de nuevo.
        </p>
        <button
          type="button"
          onClick={() => window.location.assign(import.meta.env.BASE_URL)}
          className="bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors font-medium"
        >
          Volver al inicio
        </button>
      </div>
    );
  }
}

export default ErrorBoundary;
