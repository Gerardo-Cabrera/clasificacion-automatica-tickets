import unittest
import tempfile
import os
import pandas as pd
from app import demo, procesar_tickets, TicketSystem

def simulate_csv_upload(client, csv_content):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name
    return tmp_path

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.ticket_system = TicketSystem()
        self.ticket_system.limpiar_historial()

    def test_procesar_csv_end_to_end(self):
        # Simula un archivo CSV válido
        csv_content = 'id,descripcion\n1,Mi pedido no llegó\n2,Error en mi pago\n3,Consulta general\n4,¡Es urgente!\n'
        csv_path = simulate_csv_upload(None, csv_content)
        result, urgentes_file, output_file, total, urgentes_count, duplicados = procesar_tickets(csv_path)
        self.assertEqual(total, 4)
        self.assertIn('categoria', result.columns)
        self.assertIn('urgente', result.columns)
        self.assertTrue(os.path.exists(output_file))
        if urgentes_count > 0:
            self.assertTrue(os.path.exists(urgentes_file))
        os.remove(csv_path)
        if os.path.exists(output_file):
            os.remove(output_file)
        if urgentes_file and os.path.exists(urgentes_file):
            os.remove(urgentes_file)

    def test_ticket_system_integration(self):
        # Simula la creación y limpieza de tickets
        ts = self.ticket_system
        ts.limpiar_historial()
        ts.create_ticket("Prueba integral", "pagos", True)
        ts.create_ticket("Otro ticket", "logística", False)
        tickets = ts.get_tickets()
        self.assertEqual(len(tickets), 2)
        ts.limpiar_historial()
        self.assertEqual(len(ts.get_tickets()), 0)

if __name__ == '__main__':
    unittest.main()
