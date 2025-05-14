from sunat_api import SunatAPI
from dotenv import load_dotenv
import os
from gui import SunatInvoiceAutomationGUI

def main():
    # Cargar variables de entorno
    load_dotenv()

    # Crear instancia del API con credenciales del .env o usar las por defecto
    sunat_api = SunatAPI(
        ruc=os.getenv('SUNAT_RUC'),
        client_id=os.getenv('SUNAT_CLIENT_ID'),
        client_secret=os.getenv('SUNAT_CLIENT_SECRET')
    )

    # Crear directorios necesarios
    os.makedirs('logs', exist_ok=True)
    os.makedirs('resources', exist_ok=True)
    os.makedirs('templates', exist_ok=True)

    # Iniciar la aplicación GUI
    app = SunatInvoiceAutomationGUI(sunat_api)
    app.mainloop()

if __name__ == "__main__":
    main()