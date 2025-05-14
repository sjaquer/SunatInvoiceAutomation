# 🌊 Zeus Maritime - Facturación SUNAT Automation

## 📋 Descripción
> Automatización del proceso de facturación electrónica para Zeus Maritime con integración directa a SUNAT.

## 🛠️ Características Principales
### `🔷 Gestión de Facturas`
- Lectura de Excel con productos
- Generación automática de facturas (máximo 20 items)
- Firma digital de XMLs
- Envío directo a SUNAT

### `⚫ Funcionalidades Específicas`
- Soporte para facturas de exportación
- Manejo de moneda USD/PEN
- Vista previa de facturas
- Gestión de CDR (Constancia de Recepción)

### `🔘 Interfaz Gráfica`
- Diseño minimalista y funcional
- Vista previa de facturas
- Selector de documentos
- Control de errores visual

## 📦 Requisitos
```plaintext
Python 3.8+
Certificado Digital SUNAT
Credenciales de API SUNAT
```

## ⚙️ Configuración
1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Configurar variables de entorno (.env):**
```env
SUNAT_RUC=20XXXXXXXXX
SUNAT_CLIENT_ID=your_client_id
SUNAT_CLIENT_SECRET=your_client_secret
```

3. **Ubicar certificado digital:**
```plaintext
/certs/
  ├── cert.pem    # Certificado digital
  └── key.pem     # Llave privada
```

## 🚀 Uso
### `🔷 Proceso Principal`
1. Cargar archivo Excel con productos
2. Revisar vista previa de facturas
3. Ajustar configuración si es necesario
4. Enviar a SUNAT

### `⚫ Estructura de Excel`
| Item | Product | Unit | Quantity | Unit_Price |
|------|---------|------|----------|------------|
| 1    | Rice    | BAG  | 100      | 1.440     |

## 📁 Estructura del Proyecto
```plaintext
/
├── main.py           # Punto de entrada
├── sunat_api.py      # Integración SUNAT
├── gui.py           # Interfaz gráfica
├── xml_signer.py    # Firma digital
├── cdr_handler.py   # Manejo de CDR
├── logger.py        # Sistema de logs
└── excel_reader.py  # Lectura de Excel
```

## 🔧 Mantenimiento
### `🔷 Logs`
- Los logs se almacenan en `/logs/`
- CDRs se guardan en `/cdrs/`
- Formato JSON para auditoría

### `⚫ Respaldos`
- XMLs firmados en `/signed_xmls/`
- CDRs en `/cdrs/`
- Logs mensuales en `/logs/`

## ⚠️ Consideraciones
1. **Límites SUNAT:**
   - Máximo 20 items por factura
   - Tiempo límite de envío
   - Formato específico de XMLs

2. **Seguridad:**
   - Certificado digital vigente
   - Credenciales seguras
   - Respaldo de CDRs

## 🤝 Soporte
Para soporte técnico:
- 📧 Email: soporte@zeusmaritime.com
- 💬 Teams: IT Support Channel

## 📄 Licencia
Propietario - Zeus Maritime