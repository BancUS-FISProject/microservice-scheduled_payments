# Estructura del proyecto

```bash

Plantilla hecha para los datos de ejemplo "financial analytics"

OpenAPI specification en "/api/docs"

service_name/
├── .github/                      # CI/CD (Integración Continua)
│   └── workflows/
│       └── ci.yml                # GitHub Action: instala, corre tests, chequea formato
│
├── .dockerignore                 # Archivos a ignorar en la build de Docker
├── .env                          # Plantilla de variables de entorno (para copiar a .env)
├── .gitignore
│
├── Dockerfile                    # Construcción de la imagen del servicio
├── docker-compose.yml            # Servicio + MongoDB para desarrollo
├── README.md                     # Documentación del microservicio
│
└── src/
    └── accounts_service/
        ├── __init__.py
        │
        ├── api/                  # 1. Capa de API (HTTP)
        │   ├── __init__.py
        │   ├── v1/               # Versionado /v1/
        │   │   ├── __init__.py
        │   │   └── accounts_blueprint.py  # Blueprint que contiene los endpoints de un recurso
        │   ├── auth.py           # Autenticaciones
        │
        ├── core/                 # 2. Configuración
        │   ├── __init__.py
        │   ├── config.py         # Carga variables de entorno
        │   └── extensions.py     # Configuracion de comunicaciones 
        │                         #  (base dedatos, otros microservicios)
        │
        ├── db/                   # 3. Base de datos
        │   ├── __init__.py
        │   ├── database.py       # Conexión a MongoDB (Motor)
        │   └── account_repository.py # Operaciones DB para una coleccion (tabla) 
        │
        ├── models/               # 4. Modelos Pydantic
        │   ├── __init__.py
        │   ├── account.py        # Modelos de datos (clases). Realizan validacion del tipo de dato (string, int,...)
        │
        ├── services/             # 5. Lógica de negocio
        │   ├── __init__.py
        │   └── account_service.py # crear, debitar, actualizar, etc. Validacion avanzada
        │
        ├── comms/               # 6. Comunicación
        │   ├── __init__.py
        │   ├── publisher.py      # Publica eventos (RabbitMQ, etc.)
        │   └── consumer.py       # Consume eventos externos
        │
        └── app.py               # Punto de entrada (FastAPI)
        
