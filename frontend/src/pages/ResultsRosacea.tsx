import React from 'react';
import { Thermometer } from 'lucide-react';
import ResultadoModeloLocal from '../components/results/ResultadoModeloLocal';

const ResultsRosacea: React.FC = () => (
  <ResultadoModeloLocal icono={Thermometer} tema="rojo" colorIcono="text-red-500" />
);

export default ResultsRosacea;
