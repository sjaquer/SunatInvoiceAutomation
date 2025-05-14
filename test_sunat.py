import requests
import os
import logging
from dotenv import load_dotenv
import base64
from typing import Dict, Any, Optional
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SunatAPI:
    TIPOS_COMPROBANTE = {
        "FACTURA": "01",
        "BOLETA": "03",
        "NOTA_CREDITO": "07",
        "NOTA_DEBITO": "08"
    }

    def __init__(self):
        load_dotenv()
        # Cargar credenciales del .env
        self.ruc = os.getenv("SUNAT_RUC")
        self.client_id = os.getenv("SUNAT_CLIENT_ID")
        self.client_secret = os.getenv("SUNAT_CLIENT_SECRET")
        self.usuario = os.getenv("SUNAT_USUARIO", "")  # Agregado
        self.clave = os.getenv("SUNAT_CLAVE", "")      # Agregado
        self.token = None
        
        # URLs del API según documentación
        self.token_url = "https://api-seguridad.sunat.gob.pe/v1/clientesextranet/{}/oauth2/token/"
        self.base_url = "https://api.sunat.gob.pe/v1/contribuyente/contribuyentes"

    def get_token(self) -> bool:
        """Obtener token de autenticación usando client_credentials"""
        try:
            url = self.token_url.format(self.client_id)
            
            # Datos requeridos según documentación
            data = {
                "grant_type": "client_credentials",
                "scope": "https://api.sunat.gob.pe/v1/contribuyente/contribuyentes",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            logger.debug(f"Solicitando token a: {url}")
            logger.debug(f"Data enviada: {data}")
            
            response = requests.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data["access_token"]
                logger.info("✅ Token obtenido exitosamente")
                logger.info(f"Expira en: {token_data.get('expires_in')} segundos")
                return True
            else:
                logger.error(f"❌ Error obteniendo token: {response.status_code}")
                logger.error(f"Respuesta: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error en get_token: {str(e)}")
            return False

    def test_connection(self):
        """Probar conexión al API de SUNAT"""
        try:
            if not self.token and not self.get_token():
                return False

            # Endpoint de prueba - usando GET en lugar de POST
            test_url = f"{self.base_url}/validartoken"
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }

            logger.debug(f"Probando conexión a: {test_url}")
            response = requests.get(test_url, headers=headers)

            if response.status_code == 200:
                logger.info("✅ Conexión exitosa al API de SUNAT")
                return True
            else:
                logger.error(f"❌ Error de conexión: {response.status_code}")
                logger.error(f"Respuesta: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error en test_connection: {str(e)}")
            return False

    def validar_comprobante(self, tipo: str, serie: str, numero: str, fecha: str, monto: float) -> Dict[str, Any]:
        """Validar un comprobante de pago"""
        if not self.token and not self.get_token():
            return {"success": False, "message": "No se pudo obtener el token"}

        try:
            url = f"{self.base_url}/{self.ruc}/validarcomprobante"
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }

            data = {
                "numRuc": self.ruc,
                "codComp": self.TIPOS_COMPROBANTE.get(tipo),
                "numeroSerie": serie,
                "numero": numero,
                "fechaEmision": fecha,
                "monto": monto
            }

            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "estado_cp": result["data"]["estadoCp"],
                    "estado_ruc": result["data"]["estadoRuc"],
                    "cond_domi_ruc": result["data"]["condDomiRuc"],
                    "observaciones": result["data"].get("Observaciones", [])
                }
            else:
                return {
                    "success": False,
                    "message": response.text
                }

        except Exception as e:
            logger.error(f"❌ Error validando comprobante: {str(e)}")
            return {"success": False, "message": str(e)}

def main():
    """Función principal de prueba"""
    api = SunatAPI()
    
    # Mostrar configuración
    logger.info(f"RUC: {api.ruc}")
    logger.info(f"Client ID: {api.client_id[:8]}...")
    
    # Probar directamente la validación
    resultado = api.validar_comprobante(
        tipo="FACTURA",
        serie="F001",
        numero="1",
        fecha=datetime.now().strftime("%d/%m/%Y"),
        monto=100.00
    )
    
    if resultado["success"]:
        logger.info("✅ Validación exitosa")
        logger.info(f"Estado CP: {resultado['estado_cp']}")  # 0=No existe, 1=Aceptado, 2=Anulado
        logger.info(f"Estado RUC: {resultado['estado_ruc']}")  # 00=Activo
        logger.info(f"Condición domiciliaria: {resultado['cond_domi_ruc']}")  # 00=Habido
    else:
        logger.error(f"❌ Error en validación: {resultado['message']}")

if __name__ == "__main__":
    main()
