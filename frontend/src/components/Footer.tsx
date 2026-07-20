import React from 'react';
import { Link } from 'react-router-dom';
import { Mail, Info } from 'lucide-react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-800 dark:bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div className="flex items-center">
              <img src={`${import.meta.env.BASE_URL}logo.png`} alt="Piel Sana IA" className="h-6 w-auto" />
              <span className="ml-2 text-lg font-semibold">Piel Sana IA</span>
            </div>
            <p className="mt-2 text-sm text-gray-300">
              Análisis inteligente de condiciones de la piel, ayudándote a cuidar tu salud dermatológica.
            </p>
          </div>
          
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider">Enlaces Útiles</h3>
            <ul className="mt-4 space-y-2">
              <li>
                <Link to="/" className="text-gray-300 hover:text-white">
                  Inicio
                </Link>
              </li>
              <li>
                <Link to="/about" className="text-gray-300 hover:text-white">
                  Acerca de
                </Link>
              </li>
              <li>
                <a href="#privacy" className="text-gray-300 hover:text-white">
                  Política de Privacidad
                </a>
              </li>
            </ul>
          </div>
          
          <div id="contact">
            <h3 className="text-sm font-semibold uppercase tracking-wider">Contacto</h3>
            <ul className="mt-4 space-y-2">
              <li className="flex items-center">
                <Mail className="h-5 w-5 text-gray-400 mr-2" />
                <span>thejoresp@gmail.com</span>
              </li>
              <li className="flex items-center">
                <Info className="h-5 w-5 text-gray-400 mr-2" />
                <span>Consulte con un dermatólogo para diagnósticos profesionales</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-8 border-t border-gray-700 pt-8">
          <p className="text-sm text-gray-300 text-center">
            &copy; {new Date().getFullYear()} Piel Sana IA. Todos los derechos reservados.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;