# Clasificación Automática de Tickets

Este proyecto implementa un sistema inteligente para la clasificación automática de tickets de soporte en español, usando modelos de lenguaje y una interfaz web con Gradio.

## Características principales
 - Clasificación de tickets en categorías: logística, pagos, producto defectuoso, cuenta, facturación, otros.
 - Detección automática de urgencia en los tickets.
 - Procesamiento masivo de archivos CSV y generación de reportes.
 - Integración opcional con Zendesk (requiere configuración de variables de entorno).
 - Historial de tickets simulados persistente.
 - Interfaz web amigable y lista para producción.

## Estructura del proyecto
 - `app.py`: Código principal de la aplicación y la interfaz Gradio.
 - `tests/`: Carpeta con pruebas unitarias e integrales.
 - `requirements.txt`: Dependencias del proyecto.
 - `.github/workflows/python-app.yml`: Configuración de CI con GitHub Actions.

## Ejecución desde la línea de comandos

Por defecto, al ejecutar:

```bash
python app.py
```

se abrirá la interfaz web de Gradio, donde podrás subir el archivo CSV desde el navegador.

Si deseas procesar un archivo CSV directamente desde la terminal (sin interfaz web), simplemente pasa el nombre del archivo como argumento:

```bash
python app.py mi_archivo.csv
```

Esto generará los archivos de salida con los resultados y los tickets urgentes (si los hay), sin abrir la interfaz web.

## Sobre las pruebas y unittest

Este proyecto utiliza el módulo estándar `unittest` de Python para las pruebas, ya que es suficiente para la mayoría de los casos y no requiere dependencias externas. Si prefieres usar `pytest` (por su sintaxis más concisa o funcionalidades avanzadas), puedes agregarlo a `requirements.txt` y ejecutar los tests con `pytest` sin modificar los tests existentes. 

## Pruebas
Las pruebas unitarias cubren:
 - Clasificación de texto por palabras clave.
 - Detección de urgencia.
 - Procesamiento de archivos CSV.
 - Creación y gestión de tickets simulados.


Para ejecutar las pruebas localmente:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Integración continua (CI)
El proyecto incluye un flujo de trabajo de GitHub Actions que:
 - Instala las dependencias.
 - Ejecuta las pruebas unitarias automáticamente en cada push o pull request a la rama `main`.

## Uso
1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecuta la aplicación:
   ```bash
   python app.py
   ```
3. Accede a la interfaz web en `http://localhost:7860`.

## Variables de entorno para Zendesk (opcional)
Crea un archivo `.env` con las siguientes variables si deseas integración real:
```
ZENDESK_SUBDOMAIN=tu_subdominio
ZENDESK_EMAIL=tu_email
ZENDESK_API_TOKEN=tu_token
TICKET_API_MODE=zendesk
```

## Notas
 - El sistema detecta y notifica duplicados en los archivos CSV procesados.
 - El historial de tickets simulados puede limpiarse desde el código llamando a `ticket_system.limpiar_historial()`.
 - La pestaña de clasificación individual está deshabilitada por defecto.
 - Las pruebas están en la carpeta `tests/` para mejor organización.
 - Se recomienda mantener las dependencias de pruebas en `requirements.txt` para facilitar la integración continua y la ejecución local.

---

## Demo
Se puede probar el sistema en el siguiente link:
https://gerardocabrera-clasificacion-automatica-tickets.hf.space/

Desarrollado por [Neo-Gerardo].
