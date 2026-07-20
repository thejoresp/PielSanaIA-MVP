# Frontend — convenciones

Estructura por capas y variables de entorno: [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

- **Nunca `fetch` en un componente**: usar `api/skin.ts`. Los errores llegan como `ApiError` con un
  mensaje ya listo para mostrar; renderizarlo con `<BannerError />`, **nunca** con `alert()`.
- **Clases de Tailwind siempre completas.** Interpolarlas (`bg-${color}-100`) no funciona: el purge
  del build las descarta. Por eso los temas de color son mapas de clases enteras.
- **Assets referenciados desde JSX van con `import.meta.env.BASE_URL`**, nunca con ruta absoluta
  (`src="/logo.png"`). Vite reescribe el `index.html` con la `base`, pero **no** las cadenas dentro
  del JSX: con `VITE_BASE` en subruta esas rutas dan 404.
- Todo `useEffect` que haga una petición debe cancelarse en el cleanup (flag `cancelado`).
- **Agregar un tipo de análisis** = una entrada en `constants/analisis.ts` + su ruta en `App.tsx`.
  No hay `if/else` por tipo en ningún componente.
- El **disclaimer médico** vive una sola vez, en `components/results/ResultadoLayout.tsx`. No
  duplicarlo en las páginas.
- Los cuatro flujos pasan el resultado por `navigate(state)`, que **no sobrevive a un refresh**:
  por eso existe `SinResultado`. No es un bug que haya que "arreglar" persistiendo el resultado.
- `ConsentModal` es **obligatorio** antes de cualquier análisis: consentimiento informado por la
  Ley N.º 25.326 (datos sensibles de salud). No saltearlo ni volverlo opcional.
- `main.tsx` monta un `ErrorBoundary`; sin él una excepción en render deja pantalla en blanco.
- `VITE_API_URL` debe estar definida **antes** de `npm run build`: si falta, las peticiones apuntan a
  `undefined/skin/...` y fallan en silencio hasta que el usuario sube una foto.
