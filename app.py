import os
import re
import time
import json
import requests
import gradio as gr
import pandas as pd
import torch
import logging
from dotenv import load_dotenv
from transformers import pipeline, AutoTokenizer
import sys

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# 1. MODELO ESPECÍFICO PARA ESPAÑOL
MODEL_NAME = "Recognai/zeroshot_selectra_medium"  # Modelo en español para zero-shot
CATEGORIAS = {
    "logística": re.compile(r"pedido|entrega|env[íi]o|llegada|reparto|transporte|seguimiento", re.IGNORECASE),
    "pagos": re.compile(r"pago|tarjeta|cobro|d[eé]bito|cr[eé]dito|transacci[oó]n", re.IGNORECASE),
    "producto defectuoso": re.compile(r"defectuoso|roto|rota|dañado|mal estado|no funciona|averiado|falla|pantalla", re.IGNORECASE),
    "cuenta": re.compile(r"cuenta|login|registro|acceso|contraseña|usuario|perfil", re.IGNORECASE),
    "facturación": re.compile(r"factura|recibo|impuesto|cargo|precio|valor|subtotal", re.IGNORECASE)
}
URGENCY_PATTERNS = [  # Patrones
    r"\b(urgente|inmediato|cr[íi]tico|asap|necesito ayuda ya)\b",
    r"\b(no funciona|error|fallo|roto|averiado|defectuoso|no sirve)\b",
    r"!\s*!+",
    r"\b(prioridad [1-3]|nivel [1-3])\b"
]

# 2. Clase para manejo de tickets
class TicketSystem:
    def limpiar_historial(self, filename="tickets_db.json"):
        """Limpia el historial de tickets simulados."""
        self.tickets = []
        self.next_id = 1000
        self.save_to_json(filename)
        return True
    def __init__(self):
        self.mode = os.getenv("TICKET_API_MODE", "simulated")
        self.tickets = []
        self.next_id = 1000
        
    def create_ticket(self, description: str, category: str, urgent: bool):
        """Crea un ticket en Zendesk o modo simulado"""
        if self.mode == "zendesk":
            return self._create_zendesk_ticket(description, category, urgent)
        else:
            return self._create_simulated_ticket(description, category, urgent)
    
    def _create_simulated_ticket(self, description: str, category: str, urgent: bool):
        ticket = {
            "id": self.next_id,
            "description": description,
            "category": category,
            "urgent": urgent,
            "status": "open",
            "assigned_to": "Agente Humano" if urgent else "Sistema Automático",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Simulado"
        }
        self.tickets.append(ticket)
        self.next_id += 1
        self.save_to_json()
        return ticket
    
    def _create_zendesk_ticket(self, description: str, category: str, urgent: bool):
        """Crea un ticket real en Zendesk"""
        subdomain = os.getenv("ZENDESK_SUBDOMAIN")
        email = os.getenv("ZENDESK_EMAIL")
        api_token = os.getenv("ZENDESK_API_TOKEN")
        
        priority = "urgent" if urgent else "normal"
        subject = f"[{category}] {'[URGENTE] ' if urgent else ''}Ticket Automático"
        
        data = {
            "ticket": {
                "subject": subject,
                "comment": {"body": description},
                "priority": priority,
                "tags": ["auto_classified", category],
                "type": "problem"
            }
        }
        
        try:
            response = requests.post(
                f"https://{subdomain}.zendesk.com/api/v2/tickets.json",
                json=data,
                auth=(f"{email}/token", api_token),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                ticket_data = response.json().get("ticket", {})
                ticket = {
                    "id": ticket_data["id"],
                    "description": description,
                    "category": category,
                    "urgent": urgent,
                    "status": ticket_data.get("status", "open"),
                    "assigned_to": "Agente Humano" if urgent else "Sistema Automático",
                    "created_at": ticket_data.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
                    "source": "Zendesk"
                }
                self.tickets.append(ticket)
                self.save_to_json()
                return ticket
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                return {"error": error_msg}
        
        except Exception as e:
            return {"error": str(e)}
    
    def get_tickets(self):
        return self.tickets
    
    def save_to_json(self, filename="tickets_db.json"):
        with open(filename, 'w') as f:
            json.dump(self.tickets, f, indent=2)

# 3. Cargar modelo de clasificación con manejo de errores
MODEL_LOADED = False
classifier = None

try:
    # Modelo específico para español
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    classifier = pipeline(
        "zero-shot-classification",
        model=MODEL_NAME,
        device=0 if torch.cuda.is_available() else -1
    )
    MODEL_LOADED = True
    logger.info("✅ Modelo en español cargado exitosamente")
except Exception as e:
    logger.error(f"⚠️ Error cargando modelo principal: {e}")
    logger.info("🔶 Usando modelo alternativo multilingüe...")
    try:
        MODEL_NAME = "vicgalle/xlm-roberta-large-xnli-anli"
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        classifier = pipeline(
            "zero-shot-classification",
            model=MODEL_NAME,
            device=0 if torch.cuda.is_available() else -1
        )
        MODEL_LOADED = True
        logger.info("✅ Modelo multilingüe cargado exitosamente")
    except Exception as alt_e:
        logger.error(f"⚠️ Error cargando modelo alternativo: {alt_e}")
        logger.info("🔶 Usando clasificador aleatorio como fallback")

# 4. Funciones de clasificación
def es_urgente(text: str) -> bool:
    text = text.lower()
    for pattern in URGENCY_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False

def clasificar_con_palabras_clave(text: str) -> str:
    text_lower = text.lower()
    for category, pattern in CATEGORIAS.items():
        if pattern.search(text_lower):
            return category
    return "otros"

def clasificar_texto(text: str) -> str:
    if not MODEL_LOADED or classifier is None:
        return clasificar_con_palabras_clave(text)
    
    try:
        # Usar plantillas específicas por categoría para mejor precisión
        hypothesis_templates = [
            f"Este ticket trata sobre {cat}." for cat in CATEGORIAS
        ]
        
        result = classifier(
            text, 
            candidate_labels=CATEGORIAS,
            hypothesis_template=hypothesis_templates,
            multi_label=False
        )
        
        # Umbral de confianza ajustable por categoría
        umbrales = {
            "logística": 0.4,  # Umbral más bajo por la ambigüedad natural
            "otros": 0.3,
            "default": 0.5
        }
        
        top_label = result['labels'][0]
        top_score = result['scores'][0]
        umbral = umbrales.get(top_label, umbrales["default"])
        
        if top_score >= umbral:
            return top_label
        
        # Si confianza baja, usar sistema de palabras clave
        return clasificar_con_palabras_clave(text)
    except Exception as e:
        logger.error(f"⚠️ Error en clasificación: {e}")
        return clasificar_con_palabras_clave(text)

# 5. Función para procesar archivos CSV
def procesar_tickets(input_csv, output_csv=None):
    """
    Procesa un archivo CSV con tickets y genera resultados clasificados.
    - Permite nombres únicos para archivos de salida.
    - Valida la existencia de la columna 'descripcion' (case-insensitive).
    """
    try:
        df = pd.read_csv(input_csv)
        # Buscar columna 'descripcion' de forma flexible
        desc_col = None
        for col in df.columns:
            if col.strip().lower() == 'descripcion':
                desc_col = col
                break
        if not desc_col:
            raise ValueError("El CSV debe contener una columna llamada 'descripcion' (no se encontró, revise el encabezado)")

        # Validar duplicados
        num_duplicados = df.duplicated(subset=[desc_col]).sum()
        if num_duplicados > 0:
            logger.warning(f"Se encontraron {num_duplicados} tickets duplicados (por descripción) en el archivo CSV.")
        # Nombres únicos para archivos de salida
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if not output_csv:
            output_csv = f"tickets_clasificados_{timestamp}.csv"
        urgentes_csv = f"tickets_urgentes_{timestamp}.csv"

        categorias_pred = []
        urgencias = []
        logger.info("Iniciando procesamiento de tickets...")
        for i, descripcion in enumerate(df[desc_col]):
            descripcion_str = str(descripcion)
            categoria = clasificar_texto(descripcion_str)
            categorias_pred.append(categoria)
            urgencia = es_urgente(descripcion_str)
            urgencias.append(urgencia)
            logger.info(f"Ticket {i+1}: '{descripcion_str[:30]}...' -> Categoría: {categoria}, Urgente: {urgencia}")
        df['categoria'] = categorias_pred
        df['urgente'] = urgencias
        df.to_csv(output_csv, index=False)
        logger.info(f"Resultados guardados en {output_csv}")
        urgentes = df[df['urgente']]
        if not urgentes.empty:
            urgentes.to_csv(urgentes_csv, index=False)
            logger.info(f"⚠️ {len(urgentes)} tickets urgentes guardados en '{urgentes_csv}'")
            return df, urgentes_csv, output_csv, len(df), len(urgentes), num_duplicados
        else:
            logger.info("No se encontraron tickets urgentes")
            return df, None, output_csv, len(df), 0, num_duplicados
    except Exception as e:
        logger.error(f"❌ Error procesando CSV: {e}")
        raise


# 6. Inicializar sistema de tickets para la interfaz web
ticket_system = TicketSystem()

# 7. Función para procesar tickets individuales
def procesar_ticket_individual(text):
    if not text.strip():
        return "", "", ""
    
    categoria = clasificar_texto(text)
    urgente = es_urgente(text)
    
    # Crear ticket en el sistema
    ticket = ticket_system.create_ticket(text, categoria, urgente)
    
    status = "🔴 URGENTE - Asignado a Agente Humano" if urgente else "🟢 Enviado a Sistema Automático"
    
    return categoria, "SÍ" if urgente else "NO", status

# 8. Interfaz de usuario con Gradio
with gr.Blocks(title="Sistema de Soporte Inteligente", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 Sistema Clasificador de Tickets")
    gr.Markdown(f"**Modo actual:** `{ticket_system.mode.upper()}` | **Modelo:** `{MODEL_NAME if MODEL_LOADED else 'ALEATORIO'}`")
    
    # Pestañas para diferentes funcionalidades
    """
    with gr.Tab("Clasificación Individual"):
        with gr.Row():
            with gr.Column():
                input_text = gr.Textbox(
                    label="Descripción del problema",
                    placeholder="Escribe aquí el problema del cliente...",
                    lines=4
                )
                submit_btn = gr.Button("Procesar Ticket", variant="primary")
                
                with gr.Accordion("Ejemplos Rápidos", open=False):
                    gr.Examples(
                        examples=[
                            ["Mi paquete no llegó a tiempo, ¡es urgente!"],
                            ["Error 500 al procesar mi tarjeta de crédito"],
                            ["El producto llegó con la pantalla rota"],
                            ["No puedo acceder a mi cuenta premium"],
                            ["Factura con impuestos incorrectos"]
                        ],
                        inputs=[input_text]
                    )
            
            with gr.Column():
                categoria_out = gr.Textbox(label="Categoría")
                urgencia_out = gr.Textbox(label="¿Urgente?")
                status_out = gr.Textbox(label="Estado del Ticket")
                
                with gr.Accordion("Base de Tickets", open=False):
                    ticket_db = gr.JSON(label="Tickets Registrados")
                    update_btn = gr.Button("Actualizar Base de Datos")
    """
    
    with gr.Tab("Procesar Archivo CSV"):
        with gr.Row():
            with gr.Column():
                file_input = gr.File(label="Subir CSV de tickets", file_types=[".csv"])
                process_btn = gr.Button("Procesar Archivo", variant="primary")
                
            with gr.Column():
                output_status = gr.Textbox(label="Estado de Procesamiento")
                output_download = gr.File(label="Descargar Resultados")
                urgent_download = gr.File(label="Descargar Tickets Urgentes", visible=False)
                
                with gr.Accordion("Instrucciones", open=False):
                    gr.Markdown("""
                    **Formato CSV requerido:**
                    - Debe contener columna 'descripcion'
                    - Ejemplo:
                    ```
                    id,descripcion
                    1,Mi pedido no llegó
                    2,Error en mi pago
                    ```
                    """)

    # Event handlers
    """
    submit_btn.click(
        fn=procesar_ticket_individual,
        inputs=input_text,
        outputs=[categoria_out, urgencia_out, status_out]
    )
    
    update_btn.click(
        fn=lambda: ticket_system.get_tickets(),
        inputs=[],
        outputs=ticket_db
    )
    """

    # Función wrapper para procesar CSV
    def procesar_csv_wrapper(archivo):
        """
        Procesa el archivo CSV subido y retorna mensajes y archivos de salida únicos.
        """
        if archivo is None:
            return "❌ No se subió ningún archivo", None, None, gr.update(visible=False)
        try:
            file_path = archivo.name
            result, urgentes_file, output_file, total, urgentes_count, duplicados = procesar_tickets(file_path)
            resumen = f"Total tickets procesados: {total}. "
            if duplicados > 0:
                resumen += f"Duplicados detectados: {duplicados}. "
            if urgentes_count > 0:
                resumen += f"Tickets urgentes: {urgentes_count}. "
            else:
                resumen += "No se encontraron tickets urgentes. "
            if result is not None:
                if urgentes_file:
                    return (
                        f"✅ Procesamiento completado con éxito. {resumen}Resultados: {output_file}",
                        output_file,
                        urgentes_file,
                        gr.update(visible=True)
                    )
                else:
                    return (
                        f"✅ Procesamiento completado. {resumen}Resultados: {output_file}",
                        output_file,
                        None,
                        gr.update(visible=False)
                    )
            else:
                return "❌ Error procesando el archivo", None, None, gr.update(visible=False)
        except Exception as e:
            return f"❌ Error: {str(e)}", None, None, gr.update(visible=False)

    process_btn.click(
        fn=procesar_csv_wrapper,
        inputs=file_input,
        outputs=[output_status, output_download, urgent_download, urgent_download]
    )

# 9. Ejecutar la aplicación
if __name__ == "__main__":
    # Si se pasa un archivo CSV como argumento, procesar en modo batch
    if len(sys.argv) > 1:
        input_csv = sys.argv[1]
        logger.info(f"Procesando archivo: {input_csv}")

        try:
            result, urgentes, salida, total, urgentes_count, duplicados = procesar_tickets(input_csv)
            logger.info(f"Total tickets procesados: {total}")
            logger.info(f"Duplicados detectados: {duplicados}")
            logger.info(f"Tickets urgentes: {urgentes_count}")
            logger.info(f"Archivo de resultados: {salida}")

            if urgentes:
                logger.info(f"Archivo de tickets urgentes: {urgentes}")
            else:
                logger.info("No se encontraron tickets urgentes.")
        except Exception as e:
            logger.error(f"Error procesando el archivo: {e}")
            sys.exit(1)
    else:
        # Modo interfaz web
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            show_error=True
        )
