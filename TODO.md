# TODO - TP N°1: File Transfer

## 1. Protocolo de Aplicación y Empaquetado (`src/lib/protocol.py`)
- [x] Diseñar formato de cabecera binaria fija de 11 bytes (Opcode, SeqNum, AckNum, Length).
- [x] Implementar serialización `encode()` y deserialización `decode()`.
- [x] Opcodes básicos definidos: `OP_START`, `OP_DATA`, `OP_ACK`, `OP_FIN`, `OP_ERROR`.
- [x] Soporte para envío y recepción transparente de archivos binarios.
- [x] Flujo de errores: validación de archivo inexistente en descarga y aborto por reintentos con `OP_ERROR`.

## 2. Mecanismos de Transferencia Confiable (RDT)

### Stop & Wait (`src/lib/stop_and_wait.py`)
- [x] Envío bloque a bloque esperando ACK.
- [x] Timeout de retransmisión por paquete y límite de reintentos (`MAX_TRIES = 5`).
- [x] Envío y confirmación de `OP_FIN` para cierre de transferencia.
- [x] Manejo de duplicados y orden de secuencia.
- [x] Receptor Stop & Wait con escritura directa en disco.
- [x] Espera `TIME_WAIT` al confirmar el FIN para retransmitir ACK si se pierde.

### TCP con SACK (`src/lib/sack.py`)
- [x] Ventana deslizante (sliding window) en emisor (`WINDOW_SIZE = 32`).
- [x] Seguimiento de bloques fuera de orden y generación de SACK en receptor.
- [x] Retransmisión selectiva de paquetes perdidos.
- [x] Soportar RTTs de hasta 300 ms.
- [x] Validar algorítmicamente en test unitario: 5 MB en < 2 min con 10% de pérdida y 40 ms RTT.

## 3. Clientes y Servidor Concurrente

### CLI y Parámetros (`src/lib/args_verifier.py`, `upload`, `download`, `start-server`)
- [x] Parser de argumentos CLI respetando flags de consigna (`-v`, `-q`, `-H`, `-p`, `-s`, `-d`, `-n`, `-r`).
- [x] Validaciones de puerto, existencia de archivo local y parámetros requeridos.
- [x] Protocolos normalizados a `sw` y `sack`.
- [ ] Conectar flags `-v` y `-q` con la librería estándar `logging` (reemplazar prints fijos).

### Servidor (`src/lib/file_transfer_server.py`, `src/lib/session.py`)
- [x] Servidor concurrente con `ThreadPoolExecutor`.
- [x] Gestión de sesiones por cliente (`Session`) y guardado en disco con `--storage`.
- [x] Soporte de UPLOAD y DOWNLOAD en el servidor usando Stop & Wait.
- [x] Soporte dinámico de DOWNLOAD con protocolo SACK (`SelectiveRepeat`).
- [x] Limpieza automática de sesiones terminadas o abandonadas por timeout en el servidor.

### Cliente (`src/lib/file_transfer_client.py`)
- [x] Handshake `OP_START` para inicio de conexión.
- [x] Subida (`upload`) con Stop & Wait y SACK.
- [x] Descarga (`download`) con Stop & Wait y SACK (notificando el protocolo al servidor).

## 4. Pruebas y Mininet
- [x] Suite de tests automatizados en `tests/` (SACK, Stop & Wait, Concurrencia y Archivos Grandes).
- [x] Configuración del script/entorno de topología en Mininet (`topologia.py`).
- [ ] Ejecutar prueba de 5 MB con SACK en Mininet real (validar < 2 min con `tc,loss=10,delay=20ms`).
- [ ] Captura de tráfico con Wireshark (`.pcap`) usando el dissector Lua para verificar ausencia de retransmisiones redundantes.

## 5. Mediciones y Análisis (Sección 4 del enunciado)
- [ ] Medir tiempos de transferencia de Stop & Wait vs. SACK en Mininet.
- [ ] Probar con al menos 3 tamaños distintos de archivo.
- [ ] Calcular Throughput promedio para cada caso.

## 6. Informe y Entrega Final
- [ ] Responder las 6 preguntas teóricas del enunciado.
- [ ] Redactar las secciones obligatorias de `informe.pdf` (Introducción, Hipótesis, Implementación, Pruebas, Dificultades, Conclusión).
- [x] Pasar linter `flake8` para cumplimiento de PEP 8.
- [ ] Agregar al `README.md` los ejemplos concretos de invocación de `start-server`, `upload` y `download`.
- [ ] Generar archivo `tp2.zip` con la estructura requerida.
