import React from 'react';
import { AlertCircle } from 'lucide-react';
import ResultadoModeloLocal from '../components/results/ResultadoModeloLocal';

const ResultsAcne: React.FC = () => (
  <ResultadoModeloLocal icono={AlertCircle} tema="rosa" colorIcono="text-pink-500" />
);

export default ResultsAcne;
