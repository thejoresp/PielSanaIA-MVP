import { AlertCircle, Thermometer, Sun, Crosshair, type LucideIcon } from 'lucide-react';

/**
 * Fichas de las condiciones cutáneas. **Contenido estático: vive en el frontend.**
 *
 * Antes estaba duplicado en dos lugares —`backend/data/conditions.py` (servido por
 * `GET /skin/api/condition/{nombre}`) y un array propio dentro de `ConditionsOverview`—
 * con el riesgo de que divergieran.
 *
 * Traerlo acá gana tres cosas a la vez:
 * - **Resiliencia:** `/conditions/rosacea` ya no queda en blanco si el backend está caído.
 *   Es contenido educativo, no depende de ningún modelo.
 * - **Velocidad:** se renderiza sin esperar una petición de red.
 * - **SEO:** son las páginas con más contenido real del proyecto y ahora son prerenderizables
 *   (ver S4/S9 en `docs/AUDITORIA.md`).
 *
 * El backend ya **no** expone este contenido: esta es la única fuente de verdad.
 */

export interface Condicion {
  /** Slug de la URL: `/conditions/{id}`. */
  id: string;
  titulo: string;
  descripcion: string;
  icono: LucideIcon;
  imagen: string;
  causas: string[];
  sintomas: string[];
  tratamiento: string[];
  prevencion: string[];
}

export const CONDICIONES: Condicion[] = [
  {
    id: 'acne',
    titulo: 'Acné',
    descripcion:
      'El acné es una condición común que ocurre cuando los folículos pilosos se obstruyen con grasa y células muertas de la piel, causando granos y espinillas.',
    icono: AlertCircle,
    imagen:
      'https://images.pexels.com/photos/10004287/pexels-photo-10004287.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
    causas: [
      'Cambios hormonales',
      'Exceso de producción de grasa (sebo)',
      'Bacterias',
      'Ciertos medicamentos',
      'Estrés',
    ],
    sintomas: [
      'Puntos negros y blancos',
      'Espinillas',
      'Protuberancias rojas y dolorosas',
      'Quistes',
      'Cicatrices',
    ],
    tratamiento: [
      'Limpieza suave de la piel',
      'Medicamentos tópicos (peróxido de benzoilo, retinoides)',
      'Antibióticos',
      'Terapias hormonales',
      'Evitar manipular las lesiones',
    ],
    prevencion: [
      'Lavar el rostro regularmente',
      'Evitar productos grasos',
      'No exprimir los granos',
      'Mantener el cabello limpio',
      'Usar protector solar no comedogénico',
    ],
  },
  {
    id: 'rosacea',
    titulo: 'Rosácea',
    descripcion:
      'La rosácea es una afección crónica que causa enrojecimiento y vasos sanguíneos visibles en la cara, a veces con pequeños bultos rojos llenos de pus.',
    icono: Thermometer,
    imagen:
      'https://images.pexels.com/photos/1138531/pexels-photo-1138531.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
    causas: [
      'Predisposición genética',
      'Problemas con los vasos sanguíneos faciales',
      'Ácaros microscópicos (Demodex)',
      'Bacterias intestinales (H. pylori)',
      'Desencadenantes ambientales',
    ],
    sintomas: [
      'Enrojecimiento persistente en el centro de la cara',
      'Vasos sanguíneos dilatados visibles',
      'Bultos rojos (pápulas) y pústulas',
      'Sensación de ardor o escozor',
      'Piel sensible y reactiva',
      'Engrosamiento de la piel nasal (rinofima)',
    ],
    tratamiento: [
      'Medicamentos tópicos (metronidazol, ácido azelaico)',
      'Antibióticos orales',
      'Isotretinoína (casos severos)',
      'Terapias con láser o luz pulsada',
      'Evitar desencadenantes conocidos',
    ],
    prevencion: [
      'Usar protector solar diariamente',
      'Evitar extremos de temperatura',
      'Evitar alimentos y bebidas desencadenantes',
      'Usar productos para piel sensible',
      'Mantener una buena rutina de cuidado facial',
    ],
  },
  {
    id: 'manchas',
    titulo: 'Manchas Solares',
    descripcion:
      'Las manchas solares son áreas de la piel que se oscurecen debido a la exposición prolongada al sol, también conocidas como lentigos solares.',
    icono: Sun,
    imagen:
      'https://images.pexels.com/photos/7479603/pexels-photo-7479603.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
    causas: [
      'Exposición excesiva a la radiación UV',
      'Envejecimiento de la piel',
      'Predisposición genética',
    ],
    sintomas: [
      'Manchas planas y marrones',
      'Aparición en zonas expuestas al sol',
      'No suelen causar dolor ni molestias',
    ],
    tratamiento: [
      'Cremas despigmentantes',
      'Tratamientos con láser',
      'Peelings químicos',
      'Crioterapia',
      'Protección solar diaria',
    ],
    prevencion: [
      'Evitar la exposición solar prolongada',
      'Usar protector solar de amplio espectro',
      'Utilizar ropa protectora',
      'Evitar camas solares',
      'Revisar la piel regularmente',
    ],
  },
  {
    id: 'lunares',
    titulo: 'Lunares',
    descripcion:
      'Los lunares son áreas pequeñas de pigmentación en la piel, generalmente inofensivas, pero algunos pueden evolucionar y requerir control dermatológico.',
    icono: Crosshair,
    imagen:
      'https://images.pexels.com/photos/8058606/pexels-photo-8058606.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
    causas: ['Acumulación de melanocitos', 'Factores genéticos', 'Exposición solar'],
    sintomas: [
      'Pequeñas manchas marrones o negras',
      'Pueden ser planas o elevadas',
      'Cambios en el color, tamaño o forma pueden ser signo de alerta',
    ],
    tratamiento: [
      'Observación regular',
      'Extirpación quirúrgica si es necesario',
      'Biopsia en caso de sospecha de malignidad',
      'Evitar la exposición solar excesiva',
      'Consulta dermatológica ante cambios sospechosos',
    ],
    prevencion: [
      'Usar protector solar',
      'Evitar la exposición solar intensa',
      'Autoexamen de la piel',
      'Consultar al dermatólogo ante cambios',
      'No manipular los lunares',
    ],
  },
];

/** Busca una condición por su slug de URL. Devuelve `undefined` si no existe. */
export const buscarCondicion = (id: string | undefined): Condicion | undefined =>
  CONDICIONES.find(c => c.id === id?.toLowerCase());
