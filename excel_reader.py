import pandas as pd
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'excel_reader.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('excel_reader')

class InvoiceProduct:
    """Class representing a product in an invoice"""
    
    def __init__(self, product_data: Dict[str, Any]):
        self.item = product_data.get('Item', '')
        self.product = product_data.get('Product', '')
        self.unit = product_data.get('Unit', '')
        self.quantity = float(product_data.get('Quantity', 0))
        self.unit_price = float(product_data.get('Unit_Price', 0))
        self.total = self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.quantity} {self.unit} of {self.product} - {self.item} @ {self.unit_price}"

class Invoice:
    """Class representing an invoice with multiple products"""
    
    def __init__(self, invoice_number: int, header_data: Dict[str, Any]):
        self.invoice_number = invoice_number
        self.serie = f"F{str(invoice_number).zfill(3)}"  # Automático F001, F002, etc
        self.customer_name = header_data.get('Customer_Name', '')
        self.port = header_data.get('Port', '')
        self.po = header_data.get('PO', '')
        self.products: List[InvoiceProduct] = []
        self.is_export = True  # Siempre es exportación
        self.total_amount = 0.0
        
    def add_product(self, product_data: Dict[str, Any]) -> None:
        """Añade un producto y actualiza el total"""
        product = InvoiceProduct(product_data)
        self.products.append(product)
        self.total_amount += product.total

    def get_observation(self) -> str:
        """Genera la observación en formato estandarizado"""
        return f"PORT: {self.port} / PO: {self.po}"

    def get_product_count(self) -> int:
        """Return the number of products in the invoice"""
        return len(self.products)
    
    def __str__(self):
        return (f"Invoice #{self.invoice_number} - {self.customer_name} ({self.customer_ruc})\n"
                f"Transaction: {self.transaction_type} | Currency: {self.currency} | Export: {self.is_export}\n"
                f"Products: {len(self.products)}")

class ExcelReader:
    """Class to read and parse invoice data from Excel files"""
    
    REQUIRED_COLUMNS = [
        'Invoice_Number', 'Customer_RUC', 'Customer_Name', 
        'Product_Service', 'Quantity', 'Unit_Measure', 'Description', 'Unit_Value'
    ]
    
    MAX_PRODUCTS_PER_INVOICE = 20
    
    def __init__(self):
        self.invoices: Dict[int, Invoice] = {}
        self.file_path: Optional[str] = None
        self.errors: List[str] = []
    
    def load_excel(self, file_path: str) -> bool:
        """
        Load invoice data from an Excel file
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            bool: True if file was loaded successfully, False otherwise
        """
        self.file_path = file_path
        self.invoices = {}
        self.errors = []
        
        if not os.path.exists(file_path):
            self.errors.append(f"File not found: {file_path}")
            logger.error(f"File not found: {file_path}")
            return False
        
        try:
            # Try to read the Excel file
            df = pd.read_excel(file_path)
            
            # Check if the required columns exist
            if not self._validate_columns(df):
                return False
            
            # Process the data
            return self._process_data(df)
            
        except Exception as e:
            self.errors.append(f"Error reading Excel file: {str(e)}")
            logger.error(f"Error reading Excel file: {str(e)}", exc_info=True)
            return False
    
    def _validate_columns(self, df: pd.DataFrame) -> bool:
        """
        Validate that the DataFrame has all the required columns
        
        Args:
            df: DataFrame to validate
            
        Returns:
            bool: True if all required columns exist, False otherwise
        """
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        
        if missing_columns:
            missing_cols_str = ', '.join(missing_columns)
            self.errors.append(f"Missing required columns: {missing_cols_str}")
            logger.error(f"Missing required columns: {missing_cols_str}")
            return False
        
        return True
    
    def _process_data(self, df: pd.DataFrame) -> bool:
        """Procesa los datos y separa en facturas de máximo 20 items"""
        try:
            df = df.fillna('')
            current_invoice = None
            item_count = 0
            
            for _, row in df.iterrows():
                # Si no hay factura actual o ya tiene 20 items
                if current_invoice is None or item_count >= 20:
                    if current_invoice:
                        self.invoices[current_invoice.invoice_number] = current_invoice
                    
                    # Crear nueva factura con número secuencial
                    invoice_number = len(self.invoices) + 1
                    current_invoice = Invoice(invoice_number, row.to_dict())
                    item_count = 0
                
                # Agregar producto
                current_invoice.add_product(row.to_dict())
                item_count += 1
            
            # Agregar última factura
            if current_invoice:
                self.invoices[current_invoice.invoice_number] = current_invoice
                
            return True
        except Exception as e:
            self.errors.append(f"Error procesando datos: {str(e)}")
            return False
    
    def get_invoices(self) -> List[Invoice]:
        """
        Get the list of all invoices
        
        Returns:
            List[Invoice]: List of Invoice objects
        """
        return list(self.invoices.values())
    
    def get_invoice(self, invoice_number: int) -> Optional[Invoice]:
        """
        Get a specific invoice by number
        
        Args:
            invoice_number: The invoice number to retrieve
            
        Returns:
            Optional[Invoice]: The Invoice object or None if not found
        """
        return self.invoices.get(invoice_number)
    
    def get_errors(self) -> List[str]:
        """
        Get any errors that occurred during processing
        
        Returns:
            List[str]: List of error messages
        """
        return self.errors

# Example usage
if __name__ == "__main__":
    # Create an instance of the ExcelReader
    reader = ExcelReader()
    
    # Path to the Excel file
    excel_path = os.path.join('resources', 'invoice_template.xlsx')
    
    # Load the Excel file
    if reader.load_excel(excel_path):
        print(f"Successfully loaded {len(reader.get_invoices())} invoices")
        
        # Print each invoice
        for invoice in reader.get_invoices():
            print("\n" + str(invoice))
            print(f"Products: {invoice.get_product_count()}")
            for i, product in enumerate(invoice.products, start=1):
                print(f"  {i}. {product}")
    else:
        print("Failed to load invoices:")
        for error in reader.get_errors():
            print(f"- {error}")

