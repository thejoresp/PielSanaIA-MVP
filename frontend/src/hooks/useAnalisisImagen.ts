import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analizarImagen } from '../api/skin';
import { ApiError } from '../api/client';
import type { TipoAnalisis } from '../constants/analisis';

/**
 * Estado y acciones del flujo de subida y análisis.
 *
 * Separar esto del JSX deja a `ImageUploader` como puro layout y permite razonar el
 * flujo (archivo → vista previa → análisis → navegación) sin leer 340 líneas de markup.
 */
export function useAnalisisImagen() {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [vistaPrevia, setVistaPrevia] = useState<string | null>(null);
  const [analizando, setAnalizando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lectorRef = useRef<FileReader | null>(null);
  const navigate = useNavigate();

  const limpiar = useCallback(() => {
    lectorRef.current?.abort();
    setArchivo(null);
    setVistaPrevia(null);
    setError(null);
  }, []);

  /** Valida que sea una imagen y genera la vista previa en base64. */
  const seleccionarArchivo = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('El archivo debe ser una imagen (JPEG, PNG o WebP).');
      return;
    }
    setError(null);
    setArchivo(file);

    const lector = new FileReader();
    lectorRef.current = lector;
    lector.onload = event => {
      if (typeof event.target?.result === 'string') setVistaPrevia(event.target.result);
    };
    lector.onerror = () => setError('No pudimos leer el archivo. Probá con otra imagen.');
    lector.readAsDataURL(file);
  }, []);

  /** Envía la imagen al endpoint del tipo elegido y navega a su página de resultados. */
  const analizar = useCallback(
    async (tipo: TipoAnalisis) => {
      if (!archivo) return;
      setAnalizando(true);
      setError(null);
      try {
        const resultado = await analizarImagen(tipo.endpoint, archivo);
        navigate(tipo.ruta, { state: { analysis: resultado } });
      } catch (e) {
        // El backend manda mensajes útiles en `detail` (413 tamaño, 429 rate limit,
        // 503 IA sin configurar): mostrarlos en vez de un genérico.
        setError(e instanceof ApiError ? e.message : 'Error al analizar la imagen.');
      } finally {
        setAnalizando(false);
      }
    },
    [archivo, navigate],
  );

  return { archivo, vistaPrevia, analizando, error, setError, seleccionarArchivo, limpiar, analizar };
}
