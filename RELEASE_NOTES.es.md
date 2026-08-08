# NaviXav 1.4.15

Publicado el 2026-08-08.

## Correcciones

- Las consultas sobre licencias comerciales y contribuciones utilizan ahora la dirección de contacto específica de NaviXav.
- La actualización automática ya se instala de verdad: el asistente que espera al cierre de NaviXav se lanzaba sin ninguna consola y moría de inmediato, de modo que la actualización se anunciaba como programada y la aplicación volvía a abrirse con la versión anterior. Además, el asistente mantiene su propio registro junto al instalador, para poder analizar un fallo futuro.
- Los instaladores descargados ya no se acumulan: cada actualización borra los anteriores, y el instalador hace lo mismo al terminar. Se había acumulado medio gigabyte en un equipo seguido desde las primeras versiones. Los registros se conservan, para que un fallo siga siendo analizable.

## Cambios

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
