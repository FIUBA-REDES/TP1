# Trabajo pendiente

## Distribución entre 5 integrantes

La asignación combina implementación, pruebas y documentación para que cada integrante tenga una parte funcional completa:

### Integrante 1: Stop-and-Wait y cliente de upload

- Completar handshake, ACK, `FIN` y validación de secuencias.
- Cerrar archivos correctamente y agregar tests de subida y retransmisión.
- Documentar el flujo de Stop-and-Wait.

### Integrante 2: Servidor y sesiones

- Persistir archivos, agregar `--storage` y completar el ciclo de vida de las sesiones.
- Manejar sesiones abandonadas, errores y logs.
- Probar concurrencia, cierre y limpieza de sesiones.

### Integrante 3: Descarga

- Implementar la solicitud y transferencia de descarga.
- Reconstruir archivos en el cliente y validar archivos remotos.
- Agregar tests de descarga y comparación de archivos.

### Integrante 4: Go-Back-N

- Implementar la ventana, ACKs acumulativos y retransmisiones.
- Integrar el protocolo con cliente y servidor.
- Agregar tests de pérdida, timeout, duplicados y paquetes fuera de orden.

### Integrante 5: Selective Repeat, SACK y validación

- Implementar `sack.py`, validación de paquetes y manejo de `OP_ERROR`.
- Crear el dissector Lua para Wireshark y probarlo con capturas.
- Ejecutar pruebas con Mininet, documentar resultados y actualizar el informe.

## Tareas solicitadas

- [ ] Agregar tests y verificar que la subida funcione correctamente.
- [ ] Agregar los otros dos protocolos.
- [x] Actualizar Stop-and-Wait para que retransmita los paquetes por sí mismo, en lugar de delegar los reintentos en `UdpTransport`.
- [x] Verificar los parámetros de cliente y servidor.
- [ ] Verificar puertos no utilizables u ocupados.
- [ ] Crear la extensión Lua para Wireshark.
- [ ] Implementar el proceso inverso: descarga de archivos.

## Transferencia y protocolo

- [ ] Completar Stop-and-Wait.
  - [x] Retransmitir el paquete cuando vence el timeout.
  - [x] Validar que el ACK corresponda al número de secuencia enviado.
  - [x] Retransmitir el handshake si no llega su ACK.
  - [x] Retransmitir el paquete `FIN` si no llega su ACK.
  - [x] Enviar `OP_FIN` al terminar el archivo.
  - [x] Limitar la cantidad de retransmisiones.
  - [x] Cerrar correctamente los archivos con `with open(...)`.
- [ ] Implementar Go-Back-N.
  - [ ] Definir el tamaño de ventana.
  - [ ] Mantener los paquetes pendientes de confirmación.
  - [ ] Retransmitir desde el paquete perdido cuando corresponda.
- [ ] Implementar Selective Repeat/SACK en `src/lib/sack.py`.
  - [ ] Definir el formato de los ACK selectivos.
  - [ ] Mantener paquetes recibidos fuera de orden.
  - [ ] Retransmitir únicamente los paquetes faltantes.
  - [ ] Confirmar correctamente duplicados y paquetes fuera de orden.
- [ ] Definir claramente el formato y el flujo de handshake, datos, ACK y fin.
- [ ] Validar que el cliente espere y confirme el ACK del handshake antes de enviar datos.
- [ ] Validar que `seq_num` y `ack_num` sean coherentes.

## Servidor y sesiones

- [x] Guardar en disco los bytes recibidos por cada sesión.
- [x] Usar `remote_name` para definir el nombre del archivo remoto.
- [x] Agregar al servidor una opción `--storage` para elegir el directorio de almacenamiento.
- [ ] Completar el cierre de sesión después de recibir `OP_FIN`.
- [ ] Eliminar sesiones terminadas de `FileTransferServer.sessions`.
- [ ] Agregar expiración o limpieza de sesiones abandonadas.
- [ ] Manejar correctamente sesiones incompletas y archivos parcialmente recibidos.
  - [x] Mantener el procesamiento concurrente por sesión.
- [ ] Verificar que los paquetes de una misma sesión se procesen en orden.
- [ ] Verificar que distintas sesiones puedan ejecutarse concurrentemente.
- [ ] Agregar logs claros de sesión, cliente, opcode y número de secuencia.

## Descarga

- [ ] Implementar `FileTransferClient.download()`.
- [ ] Definir el mensaje de solicitud de descarga.
- [ ] Validar que el archivo remoto exista.
- [ ] Enviar el archivo desde el servidor al cliente usando el protocolo elegido.
- [ ] Reconstruir y guardar el archivo en `destination_path`.
- [ ] Verificar la descarga comparando el archivo original y el recibido.

## Validación de paquetes y parámetros

- [x] Rechazar paquetes truncados.
- [x] Validar el tamaño mínimo del encabezado.
- [x] Validar `payload_len` contra el tamaño real del paquete.
- [x] Rechazar opcodes desconocidos.
- [ ] Manejar mensajes `OP_ERROR`.
- [x] Validar host obligatorio.
- [x] Validar puertos dentro del rango permitido, normalmente `1024` a `65535`.
- [ ] Detectar y mostrar claramente puertos ocupados (`Address already in use`).
- [x] Validar archivos de entrada existentes y regulares.
- [ ] Validar que el directorio de almacenamiento exista o pueda crearse.
- [x] Validar el protocolo seleccionado.
- [x] Validar rutas de destino de descarga.
- [x] Corregir la ayuda de `argparse` sin redefinir `-h` manualmente.
- [x] Cerrar el cliente y el transporte al finalizar una operación.

## Tests

- [ ] Test de handshake.
- [ ] Test de subida de archivo vacío.
- [ ] Test de subida de un archivo menor que un bloque.
- [ ] Test de subida de un archivo de varios bloques.
- [ ] Test de archivo binario.
- [ ] Test de descarga.
- [ ] Test de comparación subida/descarga con `cmp`.
- [ ] Test de ACK correcto.
- [ ] Test de ACK perdido y retransmisión.
- [ ] Test de paquete de datos perdido.
- [ ] Test de paquete duplicado.
- [ ] Test de paquetes fuera de orden.
- [ ] Test de timeout y límite de reintentos.
- [ ] Test de `FIN` y cierre de sesión.
- [ ] Test de paquete malformado.
- [ ] Test de opcode inválido.
- [ ] Test de puerto inválido.
- [ ] Test de puerto ocupado.
- [x] Test de dos sesiones concurrentes.
- [ ] Test de más sesiones que workers disponibles.
- [ ] Test de limpieza de sesiones terminadas.

Comando base para ejecutar los tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Mininet y red real

- [x] Verificar conectividad con `pingall`.
- [x] Ejecutar el servidor dentro de `h1`.
- [x] Ejecutar uno o más clientes dentro de `h2`.
- [ ] Probar dos transferencias simultáneas.
- [x] Probar con pérdida del 10%.
- [x] Probar con latencia configurada.
- [ ] Probar con RTT alto, de hasta aproximadamente 300 ms si lo exige el enunciado.
- [ ] Medir tiempo de transferencia.
- [ ] Medir throughput promedio.
- [ ] Repetir mediciones con distintos tamaños de archivo.
- [ ] Repetir mediciones con distintos porcentajes de pérdida.
- [ ] Capturar tráfico con `tcpdump` y analizarlo en Wireshark.
- [ ] Verificar handshake, datos, ACK, retransmisiones y `FIN` en la captura.

Comandos base:

```bash
make run-mininet
```

```text
h1 env PYTHONPATH=/home/rbarcala/MEGA/Redes/TP1/src python3 /home/rbarcala/MEGA/Redes/TP1/src/start-server -H 10.0.0.1 -p 5005 &
```

```text
h2 sh -c 'printf "contenido de prueba desde h2\\n" > /tmp/archivo-a.bin'
```

```text
h2 env PYTHONPATH=/home/rbarcala/MEGA/Redes/TP1/src python3 /home/rbarcala/MEGA/Redes/TP1/src/upload -H 10.0.0.1 -p 5005 -s /tmp/archivo-a.bin -n archivo-a.bin -r stop-and-wait
```

Captura de tráfico:

```bash
sudo tcpdump -i any -w transferencia.pcap udp port 5005
```

Filtro de Wireshark para todo el protocolo:

```wireshark
udp.port == 5005
```

Filtro para paquetes `DATA`:

```wireshark
udp.dstport == 5005 && udp.payload[0] == 0x01
```

## Extensión Lua para Wireshark

- [ ] Crear el dissector Lua del protocolo.
- [ ] Decodificar opcode.
- [ ] Decodificar número de secuencia.
- [ ] Decodificar número de ACK.
- [ ] Decodificar longitud del payload.
- [ ] Mostrar el payload.
- [ ] Registrar correctamente el dissector sobre UDP.
- [ ] Probarlo con una captura `.pcap`.
- [ ] Documentar cómo cargarlo en Wireshark.

## Makefile y dependencias

- [x] Mantener `Makefile` con nombre estándar.
- [x] Verificar automáticamente dependencias antes de `run-mininet`.
- [x] Verificar automáticamente dependencias antes de `test-mininet`.
- [x] Verificar automáticamente dependencias antes de `lint`.
- [x] Instalar Mininet y Open vSwitch solo cuando falten.
- [x] Crear el entorno virtual si no existe.
- [x] Instalar `flake8` si no existe.
- [ ] Confirmar que `make install-deps` sea el comando correcto.
- [ ] Confirmar que `make run-mininet` funcione después de una instalación limpia.

## Documentación e informe

- [ ] Documentar la arquitectura cliente-servidor.
- [ ] Documentar el formato de cada paquete.
- [ ] Documentar la máquina de estados de una sesión.
- [ ] Documentar la concurrencia por sesión.
- [ ] Explicar el manejo de pérdidas y retransmisiones.
- [ ] Incluir resultados de las pruebas.
- [ ] Incluir capturas de Wireshark.
- [ ] Incluir resultados de tiempo y throughput.
- [ ] Explicar las decisiones de diseño.
- [ ] Documentar limitaciones conocidas.
- [ ] Actualizar el `README.md` con instrucciones reproducibles.

## Orden recomendado de implementación

1. Completar y probar Stop-and-Wait.
2. Agregar `FIN`, cierre de sesión y persistencia en el servidor.
3. Implementar validación de paquetes y parámetros.
4. Implementar la descarga.
5. Agregar tests de subida y descarga.
6. Implementar Go-Back-N y Selective Repeat/SACK.
7. Probar concurrencia con varias sesiones.
8. Ejecutar las pruebas reales con Mininet.
9. Capturar y analizar tráfico en Wireshark.
10. Crear la extensión Lua.
11. Medir tiempos y throughput.
12. Completar el informe y la documentación.