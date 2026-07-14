import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  // Ruta base del build. Por defecto '/' (dominio propio o raíz).
  // Para GitHub Pages en subruta (usuario.github.io/REPO) definir
  // VITE_BASE="/PielSanaIA-MVP/" antes de `npm run build`.
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
});
