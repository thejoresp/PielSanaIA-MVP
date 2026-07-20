"""Valida los enlaces internos de la documentación.

Comprueba dos cosas en todos los `.md` del repo:

1. Que los enlaces relativos a otros `.md` apunten a un archivo que existe.
2. Que las anclas (`archivo.md#seccion`) existan como `<a id="seccion">` en el destino.

Existe porque la documentación ya se rompió una vez al mover archivos a `docs/`:
los enlaces siguieron apuntando a la raíz y nada lo detectó. Ejecutar desde la raíz:

    python .github/scripts/check_docs_links.py
"""
import os
import re
import sys

EXCLUIR = {".git", "node_modules", "dist", "venv", ".venv", "__pycache__", ".pytest_cache"}
ENLACE = re.compile(r"\[[^\]]*\]\((?P<destino>[^)\s#]+\.md)(?P<ancla>#[^)\s]+)?\)")


def markdowns(raiz="."):
    for carpeta, subdirs, archivos in os.walk(raiz):
        subdirs[:] = [d for d in subdirs if d not in EXCLUIR]
        for archivo in archivos:
            if archivo.endswith(".md"):
                yield os.path.join(carpeta, archivo)


def main():
    # La consola de Windows usa cp1252 por defecto y rompe los acentos.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    errores = []
    anclas_cache = {}

    for ruta in markdowns():
        with open(ruta, encoding="utf-8") as fh:
            contenido = fh.read()

        for linea_num, linea in enumerate(contenido.splitlines(), start=1):
            for m in ENLACE.finditer(linea):
                destino = os.path.normpath(
                    os.path.join(os.path.dirname(ruta), m.group("destino"))
                )

                if not os.path.exists(destino):
                    errores.append(
                        f"{ruta}:{linea_num}: enlace roto -> {m.group('destino')}"
                    )
                    continue

                ancla = m.group("ancla")
                if not ancla:
                    continue

                if destino not in anclas_cache:
                    with open(destino, encoding="utf-8") as fh:
                        anclas_cache[destino] = set(
                            re.findall(r'<a id="([^"]+)"', fh.read())
                        )

                nombre = ancla[1:]
                if nombre not in anclas_cache[destino]:
                    errores.append(
                        f"{ruta}:{linea_num}: ancla inexistente -> "
                        f"{m.group('destino')}{ancla}"
                    )

    if errores:
        print("Enlaces de documentación rotos:\n")
        for e in errores:
            print(f"  {e}")
        print(f"\n{len(errores)} problema(s).")
        return 1

    print("Documentación: todos los enlaces y anclas resuelven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
