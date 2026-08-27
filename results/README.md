# Resultados

Los resultados locales se ignoran por defecto porque pueden ser numerosos. Para
publicar una ejecución, añádela explícitamente a Git después de revisar que
`system.json` no contiene información que no quieras compartir.

Cada ejecución conserva el manifiesto, la descripción anónima del sistema, las
salidas brutas de `llama-bench`, el resultado normalizado y un informe Markdown.

El historial resumido y comparable está en el
[`README` principal](../README.md#historial-quick-v1). Para las ejecuciones
publicadas se versionan el manifiesto, `system.json`, los resultados JSON/CSV y
el informe. Los directorios `raw/` se conservan localmente y se excluyen de Git
porque pueden incluir rutas absolutas y telemetría voluminosa.
