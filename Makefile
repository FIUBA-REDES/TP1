SHELL := /bin/bash
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
FLAKE8 := $(VENV)/bin/flake8

# Directorios para el plugin de Wireshark
USER_PLUGIN_DIR := $(HOME)/.local/lib/wireshark/plugins
ROOT_PLUGIN_DIR := /root/.local/lib/wireshark/plugins

.PHONY: all setup install-deps ensure-deps venv init-project install-plugin lint check-mininet test-mininet run-mininet clean

all: setup

# 1. Instala paquetes del sistema requeridos (requiere sudo)
install-deps:
	sudo apt update
	sudo apt install -y mininet openvswitch-switch python3 python3-pip python3-venv wireshark iproute2

# 2. Crea el entorno virtual e instala flake8
venv:
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
		$(PIP) install --upgrade pip; \
		$(PIP) install flake8; \
	fi

# 3. Crea la estructura de carpetas, módulos y permisos solicitados
init-project: venv
	mkdir -p src/lib
	touch README.md
	touch src/lib/__init__.py
	@if [ ! -f src/upload ]; then \
		echo -e '#!/usr/bin/env python3\nimport argparse\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()' > src/upload; \
	fi
	@if [ ! -f src/download ]; then \
		echo -e '#!/usr/bin/env python3\nimport argparse\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()' > src/download; \
	fi
	@if [ ! -f src/start-server ]; then \
		echo -e '#!/usr/bin/env python3\nimport argparse\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()' > src/start-server; \
	fi
	chmod +x src/upload src/download src/start-server

# 4. Instala el plugin de Wireshark para el usuario actual y para root (Mininet)
install-plugin:
	@if [ -f src/lib/mi_plugin.lua ]; then \
		echo "Instalando plugin de Wireshark..."; \
		mkdir -p $(USER_PLUGIN_DIR); \
		cp src/lib/mi_plugin.lua $(USER_PLUGIN_DIR)/; \
		sudo mkdir -p $(ROOT_PLUGIN_DIR); \
		sudo cp src/lib/mi_plugin.lua $(ROOT_PLUGIN_DIR)/; \
		echo "Plugin instalado en $(USER_PLUGIN_DIR) y $(ROOT_PLUGIN_DIR)"; \
	else \
		echo "Advertencia: No se encontro src/lib/mi_plugin.lua. Omitiendo instalacion del plugin."; \
	fi

# Instala únicamente las dependencias que todavía no estén disponibles
ensure-deps:
	@if ! command -v mn >/dev/null 2>&1 || ! dpkg -s openvswitch-switch >/dev/null 2>&1; then \
		$(MAKE) install-deps; \
	fi
	@if [ ! -x "$(VENV)/bin/flake8" ]; then \
		$(MAKE) venv; \
	fi

# Configuración inicial completa (ahora incluye la instalación del plugin)
setup: ensure-deps init-project install-plugin

# Ejecuta el linter PEP8 exigido por la cátedra
lint: ensure-deps
	$(FLAKE8) src/

check-mininet: ensure-deps
	@if ! command -v mn >/dev/null 2>&1; then \
		echo "Error: Mininet no está instalado."; \
		echo "Ejecutá: make install-deps"; \
		exit 1; \
	fi

# Test básico de conectividad de Mininet
test-mininet: check-mininet
	sudo mn --test pingall

# Levanta Mininet con las condiciones pedidas (10% pérdida y 40ms RTT acumulados en la topología)
run-mininet: check-mininet
	sudo mn --topo single,5 --link tc,loss=5,delay=10ms

# Limpieza del entorno y sockets residuales de Mininet
clean:
	sudo mn -c
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +