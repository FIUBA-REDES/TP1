# Trabajo Práctico 1 - Redes

## Estado actual

El proyecto cuenta con un `makeFile` para preparar el entorno de desarrollo y
probar una topología básica de Mininet. La estructura actual es:

```text
src/
├── download
├── start-server
├── upload
└── lib/
	└── __init__.py
```

Los ejecutables de `src/` son esqueletos iniciales y todavía no implementan
la lógica de transferencia ni el servidor.

## Requisitos

- Ubuntu o una distribución compatible con `apt`.
- Python 3, `pip` y entornos virtuales.
- Permisos para ejecutar comandos con `sudo`.

Las dependencias del sistema se instalan automáticamente con `make setup`:

- Mininet
- Open vSwitch
- Python 3 y herramientas de entornos virtuales
- Wireshark
- `iproute2`

## Preparación del proyecto

Para instalar las dependencias del sistema, crear el entorno virtual e
inicializar la estructura del proyecto:

```bash
make setup
```

Este comando ejecuta `install-deps` e `init-project`. El entorno virtual se
crea en `venv/` y se instala `flake8` dentro de él.

También se puede ejecutar:

```bash
make all
```

`all` es equivalente a `setup`.


## Configurar plugin de Wireshark

Mover el archivo `mi_plugin.lua` dentro de la carpeta personal 
`/home/MI_CUENTA/.local/lib/wireshark/plugins/`


En una terminal ejecutar el comando 
```
sudo mn --custom src/lib/topologia.py --topo mytopo --mac
```

Abrir otra terminal y ejecutar el comando `wireshark` y seleccionar
y debería verse por pantalla `Plugin cargado correctamente`

Elegir la opción de s3-eth5 para capturar los paquetes que se envían al 
servidor a través del puerto default 5005.

## Comandos disponibles

### Verificar el estilo

```bash
make lint
```

Ejecuta `flake8` sobre `src/`.

### Probar Mininet

```bash
make test-mininet
```

Ejecuta la prueba de conectividad `pingall` de Mininet.

### Ejecutar la topología básica

```bash
make run-mininet
```

Levanta una topología `single,2` con dos hosts y enlaces configurados con
20 ms de demora y 10% de pérdida de paquetes:

```text
single,2 --link tc,loss=10,delay=20ms
```
### Ejecutar la topología custom

```
sudo mn --custom src/lib/topologia.py --topo mytopo --mac
```

Levanta una topología con 5 hosts, 4 que funcionan como clientes (del
10.0.0.1 al 10.0.0.4) y 1 que funciona como servidor (10.0.0.5) y enlaces 
configurados con 20 ms de demora y 10% de pérdida de paquetes.

### Limpiar el entorno

```bash
make clean
```

Limpia los recursos residuales de Mininet, elimina el entorno virtual `venv/`
y borra los directorios `__pycache__`.

## Flujo recomendado

```bash
make setup
make lint
make test-mininet
make run-mininet
```

## Diagrama de secuencia de Stop & Wait:
```mermaid
sequenceDiagram
    autonumber
    
    box rgb(40, 44, 52) Entorno Cliente
        participant CLI as upload.py
        participant FTC as FileTransferClient
        participant SAW as StopAndWait
    end
    
    box rgb(60, 64, 72) Capa de Red
        participant UDP as UdpTransport
    end
    
    box rgb(40, 44, 52) Entorno Servidor
        participant FTS as FileTransferServer
        participant SES as session.py
    end

    Note over CLI,SES: --- FASE 1: HANDSHAKE (Inicio de conexión) ---
    CLI->>FTC: cliente.upload("archivo.bin")
    FTC->>UDP: transport.send(OP_START, Metadata)
    UDP->>FTS: Viaja por Mininet
    FTS->>SES: Crea nueva sesión para el archivo
    SES-->>UDP: Retorna OP_ACK (Sec: 0)
    UDP-->>FTC: Confirma inicio de transferencia

    Note over CLI,SES: --- FASE 2: TRANSFERENCIA CONFIABLE ---
    FTC->>SAW: upload_file() (Delega el control)
    
    loop Lectura del Disco y Envío
        SAW->>UDP: transport.send(OP_DATA, Bloque 1, Sec: 0)
        activate SAW
        Note right of SAW: ⏱️ Timer ON (socket.settimeout)
        UDP->>FTS: Viaja por Mininet
        FTS->>SES: Guarda fragmento en buffer local
        SES-->>UDP: Retorna OP_ACK (Sec: 0)
        UDP-->>SAW: Retorna ACK al emisor
        deactivate SAW
        Note right of SAW: 🛑 Timer OFF. Espera Sec: 1
        
        SAW->>UDP: transport.send(OP_DATA, Bloque 2, Sec: 1)
        activate SAW
        Note right of SAW: ⏱️ Timer ON
        Note over UDP,FTS: 💥 PÉRDIDA: El paquete se pierde en el 10% de loss
        Note right of SAW: ⏰ TIMEOUT: Expira el timer (socket.timeout)
        SAW->>UDP: 🔄 Retransmite(OP_DATA, Bloque 2, Sec: 1)
        UDP->>FTS: Viaja por Mininet
        FTS->>SES: Guarda fragmento en buffer local
        SES-->>UDP: Retorna OP_ACK (Sec: 1)
        UDP-->>SAW: Retorna ACK al emisor
        deactivate SAW
        Note right of SAW: 🛑 Timer OFF. Espera Sec: 0
    end
    
    SAW-->>FTC: Archivo enviado por completo (return)

    Note over CLI,SES: --- FASE 3: FIN DE SESIÓN ---
    FTC->>UDP: transport.send(OP_FIN)
    UDP->>FTS: Viaja por Mininet
    FTS->>SES: self.completed = True (Cierra archivo)
    SES-->>UDP: Retorna OP_ACK
    UDP-->>FTC: Desconecta
    FTC->>CLI: Termina ejecución (exit)
```
