import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import logging
from typing import Callable, Dict, Any, Optional
from excel_reader import ExcelReader
from sunat_automation import SunatAutomation
from sunat_api import SunatAPI
import json

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'gui.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('gui')

class AutomationError(Exception):
    """Excepción personalizada para errores de automatización"""
    pass

class SunatInvoiceAutomationGUI(tk.Tk):
    """Main GUI class for the SUNAT Invoice Automation application"""
    
    def __init__(self, sunat_api: SunatAPI):
        super().__init__()
        
        self.sunat_api = sunat_api
        
        self.title("SUNAT Facturación Electrónica")
        self.geometry("1000x800")
        self.minsize(900, 700)
        
        # Configurar grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        
        # Crear frames
        self._create_empresa_frame()
        self._create_documento_frame()
        self._create_file_selection_frame()
        self._create_action_buttons()
        self._create_log_area()
        self._create_preview_frame()
        
        # Variables de control
        self.cancel_requested = False
        self.processing = False
        
        # Barra de estado
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.grid(row=5, column=0, sticky=tk.EW, padx=10, pady=5)
        
        logger.info("GUI initialized")
    
    def _create_empresa_frame(self):
        """Frame con datos de la empresa emisora"""
        empresa_frame = ttk.LabelFrame(self, text="Datos de la Empresa Emisora")
        empresa_frame.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=5)
        
        # RUC de la empresa
        ttk.Label(empresa_frame, text="RUC Emisor:").grid(row=0, column=0, padx=5, pady=5)
        self.ruc_emisor_var = tk.StringVar(value=self.sunat_api.ruc)
        ttk.Entry(empresa_frame, textvariable=self.ruc_emisor_var, state="readonly").grid(row=0, column=1, padx=5, pady=5)
        
        # Serie de factura/boleta
        ttk.Label(empresa_frame, text="Serie:").grid(row=0, column=2, padx=5, pady=5)
        self.serie_var = tk.StringVar()
        serie_entry = ttk.Entry(empresa_frame, textvariable=self.serie_var, width=10)
        serie_entry.grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(empresa_frame, text="(Ej: F001, B001)").grid(row=0, column=4, padx=5, pady=5)
    
    def _create_documento_frame(self):
        """Frame con opciones del documento y datos del receptor"""
        doc_frame = ttk.LabelFrame(self, text="Configuración de Documentos")
        doc_frame.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=5)
        doc_frame.columnconfigure(1, weight=1)
        
        # Datos del Receptor
        receptor_frame = ttk.LabelFrame(doc_frame, text="Datos del Receptor")
        receptor_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        receptor_frame.columnconfigure(1, weight=1)
        
        # Nombre o Razón Social
        ttk.Label(receptor_frame, text="Nombre/Razón Social:").grid(row=0, column=0, padx=5, pady=5)
        self.receptor_name_var = tk.StringVar()
        nombre_entry = ttk.Entry(receptor_frame, textvariable=self.receptor_name_var, width=50)
        nombre_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        # Botón para pegar desde portapapeles
        ttk.Button(
            receptor_frame, 
            text="Pegar", 
            command=self._paste_receptor_name
        ).grid(row=0, column=3, padx=5, pady=5)
        
        # Nombre del Barco
        ttk.Label(receptor_frame, text="Nombre del Barco:").grid(row=1, column=0, padx=5, pady=5)
        self.ship_name_var = tk.StringVar()
        ttk.Entry(receptor_frame, textvariable=self.ship_name_var, width=50).grid(
            row=1, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5
        )
        
        # Resto de opciones del documento
        options_frame = ttk.Frame(doc_frame)
        options_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW)
        options_frame.columnconfigure(1, weight=1)
        
        # Tipo de documento
        ttk.Label(options_frame, text="Tipo:").grid(row=0, column=0, padx=5, pady=5)
        self.doc_type_var = tk.StringVar(value="FACTURA")
        tipo_frame = ttk.Frame(options_frame)
        tipo_frame.grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(tipo_frame, text="Factura", variable=self.doc_type_var, 
                        value="FACTURA", command=self._update_doc_options).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tipo_frame, text="Boleta", variable=self.doc_type_var,
                        value="BOLETA", command=self._update_doc_options).pack(side=tk.LEFT, padx=5)
        
        # Moneda
        ttk.Label(options_frame, text="Moneda:").grid(row=1, column=0, padx=5, pady=5)
        self.currency_var = tk.StringVar(value="PEN")
        moneda_frame = ttk.Frame(options_frame)
        moneda_frame.grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(moneda_frame, text="Soles (S/)", variable=self.currency_var, 
                        value="PEN").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(moneda_frame, text="Dólares ($)", variable=self.currency_var,
                        value="USD").pack(side=tk.LEFT, padx=5)
        
        # Tipo de operación
        ttk.Label(options_frame, text="Operación:").grid(row=2, column=0, padx=5, pady=5)
        self.operation_var = tk.StringVar(value="INTERNA")
        op_frame = ttk.Frame(options_frame)
        op_frame.grid(row=2, column=1, sticky=tk.W)
        ttk.Radiobutton(op_frame, text="Venta Interna", variable=self.operation_var,
                        value="INTERNA").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(op_frame, text="Exportación", variable=self.operation_var,
                        value="EXPORTACION").pack(side=tk.LEFT, padx=5)
        
        # Forma de pago
        ttk.Label(options_frame, text="Forma de Pago:").grid(row=3, column=0, padx=5, pady=5)
        self.payment_var = tk.StringVar(value="CONTADO")
        pago_frame = ttk.Frame(options_frame)
        pago_frame.grid(row=3, column=1, sticky=tk.W)
        ttk.Radiobutton(pago_frame, text="Contado", variable=self.payment_var,
                        value="CONTADO").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(pago_frame, text="Crédito", variable=self.payment_var,
                        value="CREDITO").pack(side=tk.LEFT, padx=5)
    
    def _update_doc_options(self):
        """Actualizar opciones según el tipo de documento"""
        is_factura = self.doc_type_var.get() == "FACTURA"
        
        # Actualizar serie sugerida
        prefix = "F001" if is_factura else "B001"
        self.serie_var.set(prefix)
        
        # Habilitar/deshabilitar exportación
        for child in self.operation_var.trace_vinfo():
            self.operation_var.trace_vdelete(*child)
        self.operation_var.set("INTERNA")
        if not is_factura:
            self.operation_var.set("INTERNA")
            for radio in self.winfo_children():
                if isinstance(radio, ttk.Radiobutton) and radio.cget("value") == "EXPORTACION":
                    radio.configure(state="disabled")
        else:
            for radio in self.winfo_children():
                if isinstance(radio, ttk.Radiobutton) and radio.cget("value") == "EXPORTACION":
                    radio.configure(state="normal")
    
    def _create_file_selection_frame(self):
        """Create the frame for file selection"""
        file_frame = ttk.LabelFrame(self, text="File Selection")
        file_frame.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=10)
        file_frame.columnconfigure(1, weight=1)
        
        # Excel File Selection
        ttk.Label(file_frame, text="Excel File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.excel_path_var = tk.StringVar()
        excel_path_entry = ttk.Entry(file_frame, textvariable=self.excel_path_var)
        excel_path_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._browse_excel_file).grid(row=0, column=2, padx=5, pady=5)
        
        # Output Directory Selection
        ttk.Label(file_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_dir_var = tk.StringVar()
        output_dir_entry = ttk.Entry(file_frame, textvariable=self.output_dir_var)
        output_dir_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._browse_output_dir).grid(row=1, column=2, padx=5, pady=5)
    
    def _browse_excel_file(self):
        """Open file dialog to select Excel file"""
        filename = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if filename:
            self.excel_path_var.set(filename)
    
    def _browse_output_dir(self):
        """Open directory dialog to select output directory"""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir_var.set(dirname)
    
    def _create_action_buttons(self):
        """Create the action buttons"""
        button_frame = ttk.Frame(self)
        button_frame.grid(row=3, column=0, sticky=tk.EW, padx=10, pady=10)
        
        # Start button
        self.start_button = ttk.Button(
            button_frame, 
            text="Start Processing", 
            command=self._start_processing,
            style="Accent.TButton"
        )
        self.start_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Cancel button
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancelar",
            command=self._cancel_processing  # Vincula el método
        )
        self.cancel_button.grid(row=0, column=2, padx=5, pady=5)
        self.cancel_button.config(state=tk.DISABLED)  # Inicia deshabilitado
        
        # Clear logs button
        self.clear_button = ttk.Button(
            button_frame, 
            text="Clear Logs", 
            command=self._clear_logs
        )
        self.clear_button.grid(row=0, column=3, padx=5, pady=5)
    
    def _create_log_area(self):
        """Create the scrolled text area for logs"""
        log_frame = ttk.LabelFrame(self, text="Process Logs")
        log_frame.grid(row=4, column=0, sticky=tk.NSEW, padx=10, pady=10)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        self.log_text = ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        # Create a custom handler that redirects logs to the text widget
        self.log_handler = TextHandler(self.log_text)
        self.log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.log_handler.setFormatter(formatter)
        logger.addHandler(self.log_handler)
    
    def _clear_logs(self):
        """Clear the log area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        logger.info("Logs cleared")
    
    def _start_processing(self):
        """Start the invoice processing"""
        if not self._validate_inputs():
            return
            
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)  # Habilita el botón de cancelar
        self.status_var.set("Procesando...")
        
        # ...resto del código...

    def _run_processing(self, input_data: Dict[str, Any]):
        """Ejecutar el procesamiento de documentos"""
        try:
            self._update_progress("Cargando archivo Excel...")
            reader = ExcelReader()
            if not reader.load_excel(input_data['excel_path']):
                raise AutomationError("Error cargando archivo Excel:\n" + 
                              "\n".join(reader.get_errors()))
            
            if self.cancel_requested:
                raise AutomationError("Proceso cancelado por el usuario")
                
            self._update_progress("Iniciando proceso con SUNAT API...")
            
            # Obtener token primero
            if not self.sunat_api.get_token():
                raise AutomationError("No se pudo obtener token de SUNAT")
            
            documents = reader.get_documents()
            total_docs = len(documents)
            processed = 0
            errors = []
            
            for idx, doc in enumerate(documents, 1):
                if self.cancel_requested:
                    raise AutomationError("Proceso cancelado por el usuario")
                    
                doc_type = "factura" if input_data['document_type'] == "FACTURA" else "boleta"
                self._update_progress(f"Procesando {doc_type} {idx}/{total_docs} - #{doc.number}")
                
                # Validar comprobante primero
                validacion = self.sunat_api.validar_comprobante(
                    tipo=doc_type.upper(),
                    serie=doc.serie,
                    numero=doc.number,
                    fecha=doc.date.strftime("%d/%m/%Y"),
                    monto=doc.total
                )
                
                if not validacion['success']:
                    errors.append(f"Error validando {doc_type} #{doc.number}: {validacion['message']}")
                    continue
                
                # Si la validación es exitosa, crear el comprobante
                result = self.sunat_api.create_invoice(doc)
                if result['success']:
                    processed += 1
                else:
                    errors.append(f"Error creando {doc_type} #{doc.number}: {result['error']}")
            
            # Mostrar resumen
            if processed == total_docs:
                self._update_progress("Proceso completado exitosamente")
                messagebox.showinfo("Éxito", f"Se procesaron {total_docs} documentos correctamente")
            else:
                error_msg = f"Se procesaron {processed} de {total_docs} documentos.\n\nErrores:\n"
                error_msg += "\n".join(errors)
                messagebox.showwarning("Proceso completado con errores", error_msg)
                
        except Exception as e:
            self._handle_error(e, "procesamiento")
        finally:
            self.processing = False
            self.cancel_requested = False
            self.start_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            self.status_var.set("Listo")
    
    def _validate_inputs(self) -> bool:
        """Validar entradas antes de procesar"""
        errors = []
        
        # Validar archivo Excel
        if not self.excel_path_var.get():
            errors.append("Debe seleccionar un archivo Excel")
        
        # Validar nombre del receptor
        if not self.receptor_name_var.get().strip():
            errors.append("Debe ingresar el Nombre o Razón Social del Receptor")
        
        # Validar nombre del barco
        if not self.ship_name_var.get().strip():
            errors.append("Debe ingresar el nombre del barco")
        
        # Validar puerto
        if not self.port_var.get().strip():
            errors.append("Debe ingresar el puerto")
        
        # Validar PO
        if not self.po_var.get().strip():
            errors.append("Debe ingresar el número de PO")

        if errors:
            messagebox.showerror("Error de Validación", "\n".join(errors))
            return False
        
        return True

    def _update_progress(self, message: str):
        """Actualizar el estado del proceso"""
        self.status_var.set(message)
        logger.info(message)

    def _save_credentials(self):
        """Guardar credenciales en archivo de configuración"""
        try:
            config = {
                'ruc': self.ruc_var.get(),
                'username': self.username_var.get(),
                'last_excel_dir': os.path.dirname(self.excel_path_var.get()) if self.excel_path_var.get() else '',
                'last_output_dir': self.output_dir_var.get()
            }
            
            config_dir = os.path.join(os.path.expanduser('~'), '.sunat_automation')
            os.makedirs(config_dir, exist_ok=True)
            
            with open(os.path.join(config_dir, 'config.json'), 'w') as f:
                json.dump(config, f)
                
        except Exception as e:
            logger.error(f"Error guardando configuración: {str(e)}")

    def _handle_error(self, error: Exception, context: str):
        """Manejar errores de forma centralizada"""
        error_msg = f"Error en {context}: {str(error)}"
        logger.error(error_msg)
        self.status_var.set(f"Error: {context}")
        messagebox.showerror("Error", error_msg)

    def _cancel_processing(self):
        """Cancelar el procesamiento actual"""
        if self.processing:
            if messagebox.askyesno(
                "Confirmar Cancelación", 
                "¿Está seguro que desea cancelar el proceso?"
            ):
                logger.info("Cancelación solicitada por el usuario")
                self.cancel_requested = True
                self.cancel_button.config(state=tk.DISABLED)
                self.status_var.set("Cancelando...")

    def _create_preview_frame(self):
        """Frame para vista previa de facturas"""
        preview_frame = ttk.LabelFrame(self, text="Vista Previa de Facturas")
        preview_frame.grid(row=3, column=0, sticky=tk.NSEW, padx=10, pady=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)

        # Selector de factura
        self.invoice_var = tk.StringVar()
        self.invoice_selector = ttk.Combobox(
            preview_frame, 
            textvariable=self.invoice_var,
            state="readonly"
        )
        self.invoice_selector.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)
        self.invoice_selector.bind('<<ComboboxSelected>>', self._update_preview)

        # Área de vista previa
        preview_text = ScrolledText(preview_frame, height=15, wrap=tk.WORD)
        preview_text.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=5)
        self.preview_text = preview_text

    def _update_preview(self, event=None):
        """Actualiza la vista previa de la factura seleccionada"""
        selected = self.invoice_var.get()
        if not selected:
            return

        invoice_num = int(selected.split()[1])
        invoice = self.current_invoices.get(invoice_num)
        if not invoice:
            return

        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)

        # Cabecera con nombre del receptor
        preview = f"""FACTURA DE EXPORTACIÓN #{invoice.invoice_number}
        
Receptor: {self.receptor_name_var.get()}
Barco: {invoice.ship_name}
Tipo: {'Crédito' if invoice.transaction_type == 'CREDITO' else 'Contado'}
Moneda: {'Dólares' if invoice.currency == 'USD' else 'Soles'}
Observación: {invoice.get_observation()}

ITEMS:
{'='*50}
"""

        # Items
        total = 0
        for idx, product in enumerate(invoice.products, 1):
            line_total = product.quantity * product.unit_value
            total += line_total
            preview += f"""
    {idx}. {product.description}
       Cantidad: {product.quantity} {product.unit_measure}
       Precio unitario: {invoice.currency} {product.unit_value:.2f}
       Subtotal: {invoice.currency} {line_total:.2f}
    {'='*50}"""

        # Total
        preview += f"\nTOTAL: {invoice.currency} {total:.2f}"

        self.preview_text.insert(1.0, preview)
        self.preview_text.config(state=tk.DISABLED)

    def _paste_receptor_name(self):
        """Pegar el nombre del receptor desde el portapapeles"""
        try:
            clipboard_text = self.clipboard_get()
            self.receptor_name_var.set(clipboard_text.strip())
        except:
            messagebox.showerror("Error", "No se pudo pegar desde el portapapeles")

class TextHandler(logging.Handler):
    """Handler personalizado para redirigir logs al widget ScrolledText"""
    
    def __init__(self, text_widget: ScrolledText):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record) + '\n'
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg)
        self.text_widget.configure(state='disabled')
        self.text_widget.see(tk.END)