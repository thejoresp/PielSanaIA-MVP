import React from 'react';
import { Crosshair } from 'lucide-react';
import ResultadoModeloLocal from '../components/results/ResultadoModeloLocal';

const ResultsLunares: React.FC = () => (
  <ResultadoModeloLocal icono={Crosshair} tema="azul" colorIcono="text-blue-500" />
);

export default ResultsLunares;
