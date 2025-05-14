import logging
import os
from datetime import datetime
from typing import Optional, Any
import json

class SunatLogger:
    """Logger especializado para operaciones SUNAT"""
    
    def __init__(self, log_path: str = "logs"):
        self.log_path = log_path
        os.makedirs(log_path, exist_ok=True)
        
        # Configurar logging
        self.logger = logging.getLogger("sunat_operations")
        self.logger.setLevel(logging.DEBUG)
        
        # Handler para archivo
        log_file = os.path.join(log_path, "sunat_operations.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
    def log_operation(
        self, 
        operation: str, 
        invoice_number: str, 
        status: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registra una operación SUNAT
        
        Args:
            operation: Tipo de operación (ENVÍO, CONSULTA, etc)
            invoice_number: Número de factura
            status: Estado de la operación
            details: Detalles adicionales
        """
        try:
            # Crear registro detallado
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "invoice_number": invoice_number,
                "status": status,
                "details": details or {}
            }
            
            # Guardar en archivo JSON
            json_path = os.path.join(
                self.log_path, 
                f"operations_{datetime.now().strftime('%Y%m')}.json"
            )
            
            try:
                with open(json_path, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
            
            logs.append(log_entry)
            
            with open(json_path, 'w') as f:
                json.dump(logs, f, indent=2)
            
            # Registrar en log general
            self.logger.info(
                f"{operation} - Factura {invoice_number}: {status}"
            )
            
        except Exception as e:
            self.logger.error(
                f"Error registrando operación: {str(e)}"
            )
    
    def log_error(
        self, 
        error_type: str, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra un error"""
        try:
            self.logger.error(
                f"{error_type}: {message}",
                extra={"details": details}
            )
        except:
            self.logger.error(
                f"Error registrando error: {error_type} - {message}"
            )