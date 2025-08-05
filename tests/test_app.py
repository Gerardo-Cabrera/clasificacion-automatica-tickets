import unittest
import pandas as pd
from app import clasificar_texto, es_urgente, procesar_tickets, TicketSystem

class TestClasificacion(unittest.TestCase):
    def test_clasificar_texto_keywords(self):
        self.assertEqual(clasificar_texto("Mi pedido no llegó"), "logística")
        self.assertEqual(clasificar_texto("Error en mi pago"), "pagos")
        self.assertEqual(clasificar_texto("Pantalla rota"), "producto defectuoso")
        self.assertEqual(clasificar_texto("No puedo acceder a mi cuenta"), "cuenta")
        self.assertEqual(clasificar_texto("Factura con impuestos incorrectos"), "facturación")
        self.assertEqual(clasificar_texto("Consulta general"), "otros")

    def test_es_urgente(self):
        self.assertTrue(es_urgente("¡Es urgente!"))
        self.assertTrue(es_urgente("No funciona el producto"))
        self.assertFalse(es_urgente("Consulta sobre mi pedido"))

class TestProcesamientoCSV(unittest.TestCase):
    def test_procesar_tickets(self):
        data = {'descripcion': [
            'Mi pedido no llegó',
            'Error en mi pago',
            'Pantalla rota',
            'No puedo acceder a mi cuenta',
            'Factura con impuestos incorrectos',
            'Consulta general'
        ]}
        df = pd.DataFrame(data)
        test_csv = 'test_tickets.csv'
        df.to_csv(test_csv, index=False)
        result, urgentes_file, output_file, total, urgentes_count, duplicados = procesar_tickets(test_csv)
        self.assertEqual(total, 6)
        self.assertIn('categoria', result.columns)
        self.assertIn('urgente', result.columns)

class TestTicketSystem(unittest.TestCase):
    def test_ticket_system_simulado(self):
        ts = TicketSystem()
        ts.limpiar_historial()
        ticket = ts.create_ticket("Prueba de ticket", "logística", True)
        self.assertEqual(ticket['category'], "logística")
        self.assertTrue(ticket['urgent'])
        self.assertEqual(ticket['status'], "open")
        self.assertEqual(ticket['assigned_to'], "Agente Humano")
        self.assertEqual(ticket['source'], "Simulado")
        self.assertGreaterEqual(len(ts.get_tickets()), 1)

if __name__ == '__main__':
    unittest.main()
