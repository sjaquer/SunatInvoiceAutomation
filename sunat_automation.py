from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os
from excel_reader import Invoice
from datetime import datetime
import time
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'sunat_automation.log')),
        logging.StreamHandler()
    ]
)

class SunatAutomationError(Exception):
    """Excepción personalizada para errores de automatización"""
    pass

class SunatAutomation:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.logger = logging.getLogger('sunat_automation')
    
    def setup(self):
        """Configurar el driver de Selenium"""
        try:
            self.logger.info("Iniciando configuración del WebDriver...")
            self.logger.info(f"ChromeDriver path: {ChromeDriverManager().install()}")
            
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-extensions')
            
            self.logger.info("Opciones de Chrome configuradas")
            
            service = webdriver.chrome.service.Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.logger.info("WebDriver creado exitosamente")
            self.wait = WebDriverWait(self.driver, 20)
            
        except Exception as e:
            self.logger.error(f"Error detallado: {str(e)}", exc_info=True)
            raise
        
    def login(self, ruc: str, username: str, password: str) -> bool:
        """Login en el portal de SUNAT"""
        try:
            self.logger.info("Iniciando proceso de login en SUNAT...")
            
            # Navegar a la página de login
            self.driver.get("https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm")
            
            # Esperar y llenar RUC
            ruc_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtRuc"))
            )
            ruc_input.clear()
            ruc_input.send_keys(ruc)
            
            # Llenar usuario
            username_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtUsuario"))
            )
            username_input.clear()
            username_input.send_keys(username)
            
            # Llenar contraseña
            password_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtContrasena"))
            )
            password_input.clear()
            password_input.send_keys(password)
            
            # Hacer clic en el botón de login
            login_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btnAceptar"))
            )
            login_button.click()
            
            # Verificar si el login fue exitoso y navegar al módulo de facturación
            try:
                # Esperar que cargue el menú principal
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "menuSunat"))
                )
                
                # Navegar al módulo de facturación electrónica
                self.logger.info("Navegando al módulo de facturación...")
                
                # Buscar y hacer clic en el enlace de facturación electrónica
                facturacion_link = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Facturación Electrónica')]"))
                )
                facturacion_link.click()
                
                # Esperar que cargue la página de facturación
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "btnNuevaFactura"))
                )
                
                self.logger.info("Login exitoso y navegación completada")
                return True
                
            except Exception as e:
                self.logger.error(f"Error en navegación post-login: {str(e)}")
                return False
                    
        except Exception as e:
            self.handle_error(e, "Error en proceso de login")
            return False
            
    def create_invoice(self, invoice: Invoice) -> bool:
        """Crear una factura en SUNAT"""
        try:
            self.logger.info(f"Iniciando creación de factura #{invoice.invoice_number}")
            
            # Verificar que estamos en la página correcta
            try:
                # Intentar encontrar el botón de nueva factura
                new_invoice_btn = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "btnNuevaFactura"))
                )
            except:
                # Si no lo encuentra, intentar navegar a la página de facturación
                self.logger.info("Navegando a la página de facturación...")
                self.driver.get("https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm")
                
                facturacion_link = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Facturación Electrónica')]"))
                )
                facturacion_link.click()
                
                new_invoice_btn = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "btnNuevaFactura"))
                )
            
            # Hacer clic en nueva factura
            new_invoice_btn.click()
            
            # Esperar que cargue el formulario de factura
            self.wait.until(
                EC.presence_of_element_located((By.ID, "formNuevaFactura"))
            )
            
            # Llenar datos del cliente
            self._fill_customer_data(invoice)
            
            # Llenar productos
            self._fill_products(invoice.products)
            
            # Seleccionar tipo de transacción
            self._select_transaction_type(invoice.transaction_type)
            
            # Marcar si es exportación
            if invoice.is_export:
                self._mark_as_export()
            
            # Guardar factura
            save_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btnGuardar"))
            )
            save_button.click()
            
            # Verificar mensaje de éxito con retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    success_message = self.wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "mensaje-exito"))
                    )
                    self.logger.info(f"Factura #{invoice.invoice_number} creada exitosamente")
                    return True
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    self.logger.warning(f"Intento {attempt + 1} fallido, reintentando...")
                    time.sleep(2)
            
        except Exception as e:
            self.handle_error(e, f"Error creando factura #{invoice.invoice_number}")
            return False
    
    def _fill_customer_data(self, invoice: Invoice):
        """Llenar datos del cliente"""
        try:
            # Llenar RUC del cliente
            customer_ruc = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtRucCliente"))
            )
            customer_ruc.send_keys(invoice.customer_ruc)
            
            # Llenar nombre del cliente
            customer_name = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtNombreCliente"))
            )
            customer_name.send_keys(invoice.customer_name)
            
            # Llenar dirección
            customer_address = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtDireccionCliente"))
            )
            customer_address.send_keys(invoice.customer_address)
            
        except Exception as e:
            self.handle_error(e, "Error llenando datos del cliente")
            raise

    def handle_error(self, error: Exception, message: str) -> None:
        """Manejar errores de forma centralizada"""
        error_msg = f"{message}: {str(error)}"
        self.logger.error(error_msg)
        
        # Tomar screenshot del error
        if self.driver:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join('logs', f'error_{timestamp}.png')
            self.driver.save_screenshot(screenshot_path)
            self.logger.info(f"Screenshot guardado en: {screenshot_path}")
        
        raise SunatAutomationError(error_msg)

    def close(self):
        """Cerrar el navegador"""
        if self.driver:
            self.driver.quit()