import zipfile
import xml.etree.ElementTree as ET
import os
import logging
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CDRHandler:
    """Manejador de Constancias de Recepción (CDR) de SUNAT"""
    
    ESTADOS = {
        "0": "ACEPTADO",
        "1": "ACEPTADO CON OBSERVACIONES",
        "2": "RECHAZADO",
        "3": "EXCEPCIÓN"
    }
    
    def __init__(self, storage_path: str = "cdrs"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
    def process_cdr(self, cdr_content: bytes, invoice_number: str) -> Dict[str, Any]:
        """
        Procesa el CDR recibido de SUNAT
        
        Args:
            cdr_content: Contenido del ZIP CDR
            invoice_number: Número de factura
            
        Returns:
            Dict con estado y mensajes
        """
        try:
            # Guardar CDR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_path = os.path.join(
                self.storage_path, 
                f"CDR_{invoice_number}_{timestamp}.zip"
            )
            
            with open(zip_path, "wb") as f:
                f.write(cdr_content)
            
            # Extraer y analizar XML
            with zipfile.ZipFile(zip_path) as zf:
                xml_name = next(name for name in zf.namelist() if name.startswith('R-'))
                with zf.open(xml_name) as xml_file:
                    return self._parse_cdr_xml(xml_file.read())
                    
        except Exception as e:
            logger.error(f"Error procesando CDR: {str(e)}")
            return {
                "status": "ERROR",
                "code": "999",
                "message": f"Error procesando CDR: {str(e)}"
            }
    
    def _parse_cdr_xml(self, xml_content: bytes) -> Dict[str, Any]:
        """Analiza el XML del CDR y extrae estado y mensajes"""
        try:
            root = ET.fromstring(xml_content)
            ns = {"ar": "urn:sunat:cpe:see:gem:documentos:respuesta:1.0"}
            
            status = root.find(".//ar:ResponseCode", ns).text
            description = root.find(".//ar:Description", ns).text
            
            # Buscar notas u observaciones
            notes = []
            for note in root.findall(".//ar:Note", ns):
                notes.append(note.text)
            
            return {
                "status": self.ESTADOS.get(status, "DESCONOCIDO"),
                "code": status,
                "message": description,
                "notes": notes
            }
            
        except Exception as e:
            logger.error(f"Error analizando XML CDR: {str(e)}")
            return {
                "status": "ERROR",
                "code": "999",
                "message": f"Error analizando XML CDR: {str(e)}"
            }