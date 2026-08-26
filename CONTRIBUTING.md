# Contribuir

## Código

1. Mantén el runtime libre de dependencias Python obligatorias salvo que exista
   una justificación clara.
2. Añade pruebas para parsers, validadores y cambios de formato.
3. No modifiques una suite publicada; crea una versión nueva.
4. Ejecuta:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Resultados

Antes de contribuir una ejecución:

```bash
./bin/local-ai-bench validate results/quick-v1/<system>/<run>
```

Revisa la privacidad de `system.json` y de los logs. Añade el directorio de
resultado de forma explícita, ya que `results/**` está ignorado por defecto.
No elimines repeticiones ni errores y no edites las métricas normalizadas a
mano; si un parser necesita corregirse, regenera el informe desde los datos
brutos.

