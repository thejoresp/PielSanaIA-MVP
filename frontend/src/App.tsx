import React, { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';

/**
 * El home se importa de forma directa (es el LCP); el resto va con `lazy` para que no
 * pese en el bundle inicial de quien solo entra a la portada.
 */
const ResultsLunares = lazy(() => import('./pages/ResultsLunares'));
const ResultsAcne = lazy(() => import('./pages/ResultsAcne'));
const ResultsRosacea = lazy(() => import('./pages/ResultsRosacea'));
const ResultsOpenAI = lazy(() => import('./pages/ResultsOpenAI'));
const ConditionInfo = lazy(() => import('./pages/ConditionInfo'));
const About = lazy(() => import('./pages/About'));

const Cargando = () => <div className="text-center py-12 text-gray-600 dark:text-gray-300">Cargando...</div>;

function App() {
  return (
    <Suspense fallback={<Cargando />}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="results" element={<ResultsLunares />} />
          <Route path="results-acne" element={<ResultsAcne />} />
          <Route path="results-rosacea" element={<ResultsRosacea />} />
          <Route path="results-openai" element={<ResultsOpenAI />} />
          <Route path="conditions/:condition" element={<ConditionInfo />} />
          <Route path="about" element={<About />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

export default App;
