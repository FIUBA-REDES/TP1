# TODO - TP N°1: File Transfer

## 1. Protocolo de Aplicación y Empaquetado (`src/lib/protocol.py`)
- [x] Diseñar formato de cabecera binaria fija de 11 bytes (Opcode, SeqNum, AckNum, Length).
- [x] Implementar serialización `encode()` y deserialización `decode()`.
- [x] Opcodes básicos definidos: `OP_START`, `OP_DATA`, `OP_ACK`, `OP_FIN`, `OP_ERROR`.
- [x] Soporte para envío y recepción transparente de archivos binarios.
- [ ] Flujo de errores: contemplar y validar al menos 2 condiciones de error explícitas (ej: archivo remoto no encontrado, timeouts excedidos, etc.).

## 2. Mecanismos de Transferencia Confiable (RDT)

### Stop & Wait (`src/lib/stop_and_wait.py`)
- [x] Envío bloque a bloque esperando ACK.
- [x] Timeout de retransmisión por paquete y límite de reintentos (`MAX_TRIES = 5`).
- [x] Envío y confirmación de `OP_FIN` para cierre de transferencia.
- [x] Manejo de duplicados y orden de secuencia.
- [x] Receptor Stop & Wait con escritura directa en disco.

### TCP con SACK (`src/lib/sack.py`)
- [ ] Implementar la ventana deslizante (sliding window) en el emisor.
- [ ] Implementar en el receptor el seguimiento de paquetes fuera de orden y generación de bloques SACK.
- [ ] Retransmisión selectiva de paquetes perdidos (evitando retransmitir datos ya confirmados).
- [ ] Soportar RTTs de hasta 300 ms.
- [ ] Cumplir requisito crítico: transferir 5 MB en < 2 minutos con 10% de pérdida y 40 ms de RTT.

## 3. Clientes y Servidor Concurrente

### CLI y Parámetros (`src/lib/args_verifier.py`, `upload`, `download`, `start-server`)
- [x] Parser de argumentos CLI respetando flags de consigna (`-v`, `-q`, `-H`, `-p`, `-s`, `-d`, `-n`, `-r`).
- [x] Validaciones de puerto, existencia de archivo local y parámetros requeridos.
- [ ] Corregir opciones de protocolo: cambiar `go-back-n` / `selective-repeat` por `sack`.

### Servidor (`src/lib/file_transfer_server.py`, `src/lib/session.py`)
- [x] Servidor concurrente con `ThreadPoolExecutor`.
- [x] Gestión de sesiones por cliente (`Session`) y reensamblado de datos en buffer.
- [x] Guardado en disco con `--storage` / `storage_dir`.
- [x] Soporte de UPLOAD y DOWNLOAD en el servidor usando Stop & Wait.
- [ ] Integrar el servidor con el protocolo SACK.
- [ ] Limpieza automática de sesiones terminadas o abandonadas por timeout.

### Cliente (`src/lib/file_transfer_client.py`)
- [x] Handshake `OP_START` para inicio de conexión.
- [x] Subida (`upload`) con Stop & Wait.
- [x] Descarga (`download`) con Stop & Wait.
- [ ] Integrar cliente con SACK para subida y descarga.

## 4. Pruebas y Mininet
- [x] Suite de tests unitarios/integración en `tests/` para Stop & Wait y concurrencia.
- [X] Configuración del script/entorno de topología en Mininet.
- [X] Pruebas con enlace al 10% de pérdida en ambos sentidos.
- [X] Pruebas con RTT de 40 ms
- [ ] Captura de tráfico con Wireshark (`.pcap`) para verificar que SACK no retransmita datos redundantes.

## 5. Mediciones y Análisis (Sección 4 del enunciado)
- [ ] Medir tiempos de transferencia de Stop & Wait vs. SACK.
- [ ] Probar con al menos 3 tamaños distintos de archivo.
- [ ] Variar tasas de pérdida y calcular el Throughput promedio para cada caso.

## 6. Informe y Entrega Final
- [ ] Responder las 6 preguntas teóricas del enunciado.
- [ ] Redactar las secciones obligatorias del `informe.pdf` (Introducción, Hipótesis, Implementación, Pruebas, Dificultades, Conclusión).
- [ ] Pasar el linter `flake8` para asegurar cumplimiento de PEP8.
- [ ] Documentar en `README.md` los comandos exactos de ejecución.
- [ ] Generar archivo `tp2.zip` con la estructura requerida.
