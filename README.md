# WhatBot – Resumen General
Qué es WhatBot
Para qué sirve
Arquitectura limpia
Estructura del proyecto
Cómo instalar
Cómo ejecutar
Tecnologías usadas
# WhatBot – Chatbot Inmobiliario con WhatsApp, OpenAI y Clean Architecture

WhatBot es un chatbot inmobiliario que permite a los usuarios consultar propiedades a través de **WhatsApp**.  
El bot responde preguntas utilizando información de un **catálogo inmobiliario en PDF** y generación de respuestas mediante **OpenAI**.

El sistema está diseñado utilizando **Clean Architecture**, lo que permite separar claramente la lógica del negocio, la infraestructura y la presentación.

---

# Características principales

- Integración con **WhatsApp Cloud API**
- Respuestas inteligentes con **OpenAI**
- Búsqueda contextual en **catálogo inmobiliario PDF**
- Registro de conversaciones en **SQLite**
- Arquitectura **Clean Architecture**
- Código modular y escalable
- Fácil despliegue en **Render / Cloud**

---

# Arquitectura del sistema

El proyecto está organizado siguiendo una arquitectura limpia:

Cada capa tiene responsabilidades específicas para mantener el sistema desacoplado y mantenible.

---

# Estructura del proyecto
Presentation
↓
Application
↓
Infrastructure
↓
Domain

Cada capa tiene responsabilidades específicas para mantener el sistema desacoplado y mantenible.

---

# Estructura del proyecto
WHATBOT
│
├── app
│ ├── presentation
│ │ └── webhook.py
│ │
│ ├── application
│ │ ├── procesar_mensaje.py
│ │ └── generar_respuesta.py
│ │
│ ├── domain
│ │ └── models.py
│ │
│ ├── infrastructure
│ │ ├── database.py
│ │ ├── log_repository.py
│ │ ├── pdf_service.py
│ │ ├── openai_service.py
│ │ └── whatsapp_service.py
│ │
│ └── utils
│ └── text_utils.py
│
├── Docs
│ └── catalogo_inmobiliaria.pdf
│
├── templates
│ └── index.html
│
├── instance
│ └── whatbot.db
│
├── main.py
├── requirements.txt
└── README.md

---

# Descripción de capas

## Presentation

Responsable de recibir solicitudes externas y devolver respuestas.

Ejemplo:

- Webhook de WhatsApp
- Renderizado de la página de logs

Archivo principal:

--- app/presentation/webhook.py

## Application

Contiene los **casos de uso del sistema**.

Coordina el flujo entre las capas sin depender directamente de infraestructura.

Ejemplos:

- procesar mensajes de usuario
- generar respuestas del chatbot

Archivos:
procesar_mensaje.py
generar_respuesta.py

---

## Domain

Contiene las **entidades del sistema**.

Representa los modelos principales del negocio.

Ejemplo:

---

## Domain

Contiene las **entidades del sistema**.

Representa los modelos principales del negocio.

Ejemplo:
Log

Archivo:domain/models.py

---

## Infrastructure

Se encarga de la comunicación con tecnologías externas.

Incluye:

- Base de datos
- API de WhatsApp
- API de OpenAI
- Lectura del catálogo PDF

Archivos:
database.py
log_repository.py
pdf_service.py
openai_service.py
whatsapp_service.py

---

## Utils

Funciones auxiliares reutilizables.

Ejemplo:

- normalización de texto
- expansión de sinónimos
- procesamiento de líneas del PDF

Archivo:app/utils/text_utils.py

---

# Flujo del sistema

Cuando un usuario envía un mensaje a WhatsApp:

1. WhatsApp envía el mensaje al **Webhook**
2. La capa **Presentation** recibe el evento
3. La capa **Application** procesa la consulta
4. Se consulta el **catálogo PDF**
5. Se genera respuesta con **OpenAI**
6. Se registra la conversación en la base de datos
7. Se envía la respuesta al usuario por WhatsApp

---

# Variables de entorno

Crear un archivo `.env` en la raíz del proyecto.

Ejemplo:
OPENAI_API_KEY=tu_api_key

CHAT_MODEL=gpt-4o-mini

PDF_PATH=Docs/catalogo_inmobiliaria.pdf

WHATSAPP_TOKEN=tu_token_de_meta

WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id

---

# Instalación

## 1 Crear entorno virtual
python -m venv venv

---

## 2 Activar entorno

Windows:venv\Scripts\activate

Linux / Mac:
source venv/bin/activate

---

## 3 Instalar dependencias
pip install -r requirements.txt

---
## 4 Ejecutar el proyecto

---
## 4 Ejecutar el proyecto
python main.py
El servidor se ejecutará en:
http://localhost

---
# Base de datos

El proyecto utiliza **SQLite** para registrar conversaciones.

Archivo:instance/whatbot.db

Se almacena:

- número de usuario
- tipo de mensaje
- texto
- fecha y hora

---

# Tecnologías utilizadas

- Python
- Flask
- SQLAlchemy
- OpenAI API
- WhatsApp Cloud API
- PyPDF
- SQLite

---

# Posibles mejoras futuras

El proyecto puede escalar fácilmente gracias a su arquitectura modular.

Posibles extensiones:

- envío de **imágenes de propiedades**
- integración con **base de datos inmobiliaria**
- búsqueda por **precio, ciudad o metraje**
- uso de **embeddings y vector search**
- panel administrativo para gestión de propiedades
- analítica de conversaciones
- integración con CRM inmobiliario

---

# Autor

Proyecto desarrollado por **Nelson**.

Chatbot inmobiliario diseñado para automatizar la atención a clientes y facilitar la consulta de propiedades a través de WhatsApp.