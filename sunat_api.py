import requests
import json
import base64
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from excel_reader import Invoice
from dotenv import load_dotenv
import os
import xml.etree.ElementTree as ET
import hashlib
import zipfile

class SunatAPI:
    def __init__(self, ruc: str = None, client_id: str = None, client_secret: str = None):
        """Inicializa el API de SUNAT con credenciales"""
        load_dotenv()
        self.ruc = ruc or os.getenv("SUNAT_RUC")
        self.client_id = client_id or os.getenv("SUNAT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SUNAT_CLIENT_SECRET")
        self.token = None
        self.logger = logging.getLogger('sunat_api')
        
        # URLs del API
        self.token_url = "https://api-seguridad.sunat.gob.pe/v1/clientesextranet/{}/oauth2/token/"
        self.base_url = "https://api.sunat.gob.pe/v1/contribuyente/contribuyentes"
        
        self.logger.info(f"SunatAPI inicializado para RUC: {self.ruc}")

    # Constantes para XML
    XML_NAMESPACES = {
        'xmlns': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        'ds': "http://www.w3.org/2000/09/xmldsig#",
        'ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    }

    def get_token(self) -> bool:
        """Obtener token de autenticación"""
        try:
            url = self.token_url.format(self.client_id)
            
            data = {
                "grant_type": "client_credentials",
                "scope": "https://api.sunat.gob.pe/v1/contribuyente/contribuyentes",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            self.logger.debug(f"Solicitando token a: {url}")
            response = requests.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.logger.info("Token obtenido exitosamente")
                return True
            else:
                self.logger.error(f"Error obteniendo token: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error en autenticación: {str(e)}")
            return False

    def create_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """Crea y envía una factura a SUNAT"""
        try:
            # Generar XML
            xml_content = self._generate_xml(invoice)
            
            # Crear nombre de archivo
            filename = f"{self.ruc}-{'01' if invoice.is_factura else '03'}-{invoice.serie}-{invoice.invoice_number}"
            
            # Crear ZIP
            zip_filename = f"{filename}.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zf:
                zf.writestr(f"{filename}.xml", xml_content)
            
            # Enviar a SUNAT
            if not self.token and not self.get_token():
                raise Exception("No se pudo obtener el token")
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/zip"
            }
            
            with open(zip_filename, 'rb') as f:
                response = requests.post(
                    f"{self.base_url}/contribuyente/gem/comprobantes/envio",
                    headers=headers,
                    data=f.read()
                )
            
            # Procesar respuesta
            if response.status_code == 200:
                cdr = response.json()
                self.logger.info(f"Comprobante {filename} enviado exitosamente")
                return {
                    "success": True,
                    "cdr": cdr,
                    "xml_hash": hashlib.sha256(xml_content).hexdigest()
                }
            else:
                self.logger.error(f"Error enviando comprobante: {response.text}")
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            self.logger.error(f"Error en create_invoice: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_xml(self, invoice: Invoice) -> str:
        """Genera el XML UBL 2.1 para SUNAT"""
        try:
            # Crear elemento raíz con namespaces
            root = ET.Element("Invoice", self.XML_NAMESPACES)
            
            # Versión UBL y personalización
            ET.SubElement(root, "cbc:UBLVersionID").text = "2.1"
            ET.SubElement(root, "cbc:CustomizationID").text = "2.0"
            
            # ID del documento (serie-número)
            ET.SubElement(root, "cbc:ID").text = f"{invoice.serie}-{invoice.invoice_number}"
            
            # Fecha y hora de emisión
            now = datetime.now()
            ET.SubElement(root, "cbc:IssueDate").text = now.strftime("%Y-%m-%d")
            ET.SubElement(root, "cbc:IssueTime").text = now.strftime("%H:%M:%S")
            
            # Tipo de documento
            ET.SubElement(root, "cbc:InvoiceTypeCode").text = "01" if invoice.is_factura else "03"
            
            # Moneda
            ET.SubElement(root, "cbc:DocumentCurrencyCode").text = "PEN" if invoice.currency == "SOL" else "USD"
            
            # Datos del emisor
            supplier = ET.SubElement(root, "cac:AccountingSupplierParty")
            party = ET.SubElement(supplier, "cac:Party")
            
            party_identification = ET.SubElement(party, "cac:PartyIdentification")
            ET.SubElement(party_identification, "cbc:ID", schemeID="6").text = self.ruc
            
            party_name = ET.SubElement(party, "cac:PartyName")
            ET.SubElement(party_name, "cbc:Name").text = invoice.emisor_name
            
            # Datos del cliente
            customer = ET.SubElement(root, "cac:AccountingCustomerParty")
            customer_party = ET.SubElement(customer, "cac:Party")
            
            customer_identification = ET.SubElement(customer_party, "cac:PartyIdentification")
            doc_type = "6" if len(invoice.customer_ruc) == 11 else "1"
            ET.SubElement(customer_identification, "cbc:ID", schemeID=doc_type).text = invoice.customer_ruc
            
            # Totales
            tax_total = ET.SubElement(root, "cac:TaxTotal")
            total_igv = sum(self._calculate_igv(item.unit_value * item.quantity) for item in invoice.products)
            ET.SubElement(tax_total, "cbc:TaxAmount", currencyID=invoice.currency).text = str(total_igv)
            
            # Items
            for idx, item in enumerate(invoice.products, 1):
                self._add_invoice_line(root, idx, item, invoice.currency)
            
            # Generar XML
            xml_string = ET.tostring(root, encoding="ISO-8859-1")
            
            # Calcular hash
            xml_hash = hashlib.sha256(xml_string).hexdigest()
            self.logger.info(f"XML generado con hash: {xml_hash}")
            
            return xml_string
            
        except Exception as e:
            self.logger.error(f"Error generando XML: {str(e)}")
            raise

    def _add_invoice_line(self, root: ET.Element, line_number: int, product: Any, currency: str):
        """Agrega una línea de factura al XML"""
        line = ET.SubElement(root, "cac:InvoiceLine")
        ET.SubElement(line, "cbc:ID").text = str(line_number)
        
        # Cantidad
        ET.SubElement(line, "cbc:InvoicedQuantity", 
                     unitCode=product.unit_measure).text = str(product.quantity)
        
        # Valores
        unit_value = product.unit_value
        igv = self._calculate_igv(unit_value)
        line_total = unit_value * product.quantity
        
        # Precio unitario
        price = ET.SubElement(line, "cac:Price")
        ET.SubElement(price, "cbc:PriceAmount", 
                     currencyID=currency).text = str(unit_value)
        
        # IGV
        tax_total = ET.SubElement(line, "cac:TaxTotal")
        ET.SubElement(tax_total, "cbc:TaxAmount", 
                     currencyID=currency).text = str(igv * product.quantity)
        
        # Descripción
        item = ET.SubElement(line, "cac:Item")
        ET.SubElement(item, "cbc:Description").text = product.description

    def _format_invoice_data(self, invoice: Invoice) -> Dict[str, Any]:
        """Convertir objeto Invoice al formato requerido por SUNAT"""
        return {
            "emisor": {
                "numRuc": self.ruc,
                "tipDocu": "6"
            },
            "receptor": {
                "numDocu": invoice.customer_ruc,
                "tipDocu": "6",
                "rznSocial": invoice.customer_name,
                "direccion": invoice.customer_address
            },
            "comprobante": {
                "tipComp": "01",  # Factura
                "serie": f"F{datetime.now().year}",
                "numero": invoice.invoice_number,
                "fechaEmision": datetime.now().strftime("%Y-%m-%d"),
                "moneda": "PEN" if invoice.currency == "SOL" else "USD",
                "formaPago": {
                    "tipo": "Contado" if invoice.transaction_type == "CASH" else "Credito"
                },
                "items": self._format_items(invoice.products)
            }
        }

    def _format_items(self, products: list) -> list:
        """Convertir productos al formato requerido por SUNAT"""
        items = []
        for product in products:
            items.append({
                "codigo": product.code,
                "descripcion": product.description,
                "unidad": product.unit_measure,
                "cantidad": product.quantity,
                "valorUnitario": product.unit_value,
                "igv": self._calculate_igv(product.unit_value),
                "tipAfectacion": "10"  # Gravado - Operación Onerosa
            })
        return items

    def _calculate_igv(self, unit_value: float) -> float:
        """Calcular IGV (18%)"""
        return round(unit_value * 0.18, 2)

    def test_connection(self) -> bool:
        """Prueba la conexión y las credenciales"""
        try:
            self.logger.info("Probando conexión con SUNAT...")
            if self.get_token():
                self.logger.info("Conexión exitosa - Token obtenido")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error probando conexión: {str(e)}")
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

            self.logger.debug(f"Validando comprobante: {data}")
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
            self.logger.error(f"Error validando comprobante: {str(e)}")
            return {"success": False, "message": str(e)}

