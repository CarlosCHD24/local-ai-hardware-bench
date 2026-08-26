# Añadir un runtime

Los adaptadores implementan `prepare`, `command` y `parse` definidos en
`runtimes/base.py`. Un runtime nuevo debe:

- Fijar una versión o revisión reproducible.
- Conservar la salida bruta.
- Traducir sus métricas al mismo significado y unidades.
- Registrar backend, hilos, offload y parámetros relevantes.
- Declarar si mide lo mismo que `llama-bench` o necesita una suite diferente.

MLX, ONNX Runtime y servidores OpenAI-compatible deben comenzar como suites
separadas. Solo deberían incorporarse a una comparación común después de
validar que el trabajo medido es equivalente.

