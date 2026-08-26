# Privacidad de resultados

El detector no recopila hostname, usuario, direcciones de red ni números de
serie. Aun así, antes de publicar una ejecución se deben revisar:

- `system.json`
- `manifest.json`
- archivos `raw/*.stderr.txt`

Algunas versiones de drivers o herramientas pueden imprimir rutas locales en
mensajes de error. El proyecto reemplaza el directorio de datos por una variable
en el comando registrado, pero no puede garantizar el contenido de stderr
producido por herramientas externas.

Utiliza un `system-id` descriptivo pero anónimo, como `desktop-rtx4070-32gb`.
