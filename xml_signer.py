from signxml import XMLSigner, methods
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import serialization
import logging
import os
from datetime import datetime
from typing import Optional, Union
from lxml import etree

logger = logging.getLogger(__name__)

class XMLSignerError(Exception):
    """Excepción específica para errores de firma XML"""
    pass

class SunatXMLSigner:
    def __init__(self, cert_path: str, key_path: str, password: Optional[str] = None):
        """
        Inicializa el firmador XML
        
        Args:
            cert_path: Ruta al certificado digital (.cer o .pem)
            key_path: Ruta a la llave privada (.key o .pem)
            password: Contraseña de la llave privada (opcional)
        """
        self.cert_path = cert_path
        self.key_path = key_path
        self.password = password.encode() if password else None
        self._load_certificate()
        
    def _load_certificate(self):
        """Carga el certificado digital y la llave privada"""
        try:
            with open(self.cert_path, 'rb') as cert_file:
                self.certificate = load_pem_x509_certificate(cert_file.read())
            
            with open(self.key_path, 'rb') as key_file:
                self.private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=self.password
                )
                
            logger.info("Certificado digital cargado exitosamente")
            
        except Exception as e:
            logger.error(f"Error cargando certificado: {str(e)}")
            raise XMLSignerError(f"Error cargando certificado: {str(e)}")
    
    def sign_xml(self, xml_content: Union[str, bytes, etree._Element]) -> str:
        """
        Firma el XML usando el certificado digital
        
        Args:
            xml_content: Contenido XML a firmar (str, bytes o ElementTree)
            
        Returns:
            str: XML firmado
        """
        try:
            # Convertir el contenido a ElementTree si es necesario
            if isinstance(xml_content, str):
                xml_content = etree.fromstring(xml_content.encode())
            elif isinstance(xml_content, bytes):
                xml_content = etree.fromstring(xml_content)
            
            # Crear el firmador
            signer = XMLSigner(
                method=methods.enveloped,
                signature_algorithm="rsa-sha256",
                digest_algorithm="sha256",
                c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
            )
            
            # Firmar el XML
            signed_root = signer.sign(
                xml_content,
                key=self.private_key,
                cert=self.certificate
            )
            
            # Convertir a string
            signed_xml = etree.tostring(
                signed_root,
                encoding='UTF-8',
                xml_declaration=True
            ).decode()
            
            logger.info("XML firmado exitosamente")
            return signed_xml
            
        except Exception as e:
            logger.error(f"Error firmando XML: {str(e)}")
            raise XMLSignerError(f"Error firmando XML: {str(e)}")