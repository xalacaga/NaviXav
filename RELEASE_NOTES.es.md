# NaviXav 1.4.12

Publicado el 2026-08-08.

## Correcciones

- Las actualizaciones automáticas esperan ahora a que el proceso anterior de NaviXav se cierre por completo, reinstalan en la carpeta realmente utilizada y conservan un registro de instalación, evitando que la versión anterior se reinicie y vuelva a ofrecer la misma actualización.
- La preparación de una Release admite ahora una categoría Novedades o Correcciones vacía sin desplazar los argumentos PowerShell siguientes ni interrumpir la publicación.

## Cambios

- Correction bug.
- Bug de versioning.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
