# SleepMetrics

Plataforma de análisis de patrones de sueño. Registra tus noches y tus hábitos diarios, calcula un **score de calidad de 0 a 100** con una fórmula ponderada y expone métricas agregadas y correlaciones entre hábitos y descanso.

**Demo:** _(pendiente de desplegar)_ · **API:** _(pendiente de desplegar)_

> **Pruébalo sin registrarte.** El botón *"Probar sin registrarme"* del login crea al instante una cuenta temporal, con tres meses de datos de ejemplo, exclusiva para ti. Puedes usarla como quieras: se elimina sola a las 24 horas.

---

## Índice

- [Qué hace](#qué-hace)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [El algoritmo de scoring](#el-algoritmo-de-scoring)
- [Modelo de datos](#modelo-de-datos)
- [API](#api)
- [Capturas](#capturas)
- [Ejecutar en local](#ejecutar-en-local)
- [Migraciones de base de datos](#migraciones-de-base-de-datos)
- [Despliegue](#despliegue)
- [Decisiones técnicas](#decisiones-técnicas)
- [Convenciones de commits](#convenciones-de-commits)

---

## Qué hace

SleepMetrics resuelve un problema concreto: la mayoría de aplicaciones de sueño te dicen *cuánto* dormiste, pero no *por qué* dormiste mal.

1. **Registras una noche** — cuándo te acostaste, cuándo despertaste, cuántas veces te desvelaste.
2. **Registras tus hábitos del día** — cafeína consumida y a qué hora, minutos de pantalla antes de dormir, ejercicio.
3. **La aplicación calcula un score** de 0 a 100 desglosado por factor, de modo que ves exactamente qué te está restando puntos.
4. **Con varias noches acumuladas**, calcula tu mejor y peor día de la semana y la correlación estadística entre cada hábito y tu calidad de sueño.

---

## Stack tecnológico

### Backend
| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11 |
| Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (estilo declarativo tipado) |
| Driver | psycopg2-binary |
| Validación | Pydantic v2 + pydantic-settings |
| Autenticación | python-jose (JWT) + passlib (bcrypt) |
| Migraciones | Alembic |
| Servidor | Uvicorn |

### Base de datos
PostgreSQL 15+ gestionado en **Supabase** (usado exclusivamente como Postgres administrado, sin su capa de auth ni su SDK de cliente).

### Frontend
| Componente | Tecnología |
|---|---|
| Framework | Next.js 14 (App Router) |
| Lenguaje | TypeScript |
| Estilos | Tailwind CSS 3 |
| HTTP | Axios (con interceptores) |
| Gráficas | Recharts 3 |

### Despliegue
Backend en **Render** · Base de datos en **Supabase** · Frontend en **Vercel**. Todo en capa gratuita.

---

## Arquitectura

### Vista general

```
┌──────────────────────┐         ┌──────────────────────┐        ┌────────────────────┐
│   NAVEGADOR          │  HTTPS  │   RENDER             │  TLS   │   SUPABASE         │
│                      │ ──────► │                      │ ─────► │                    │
│  Next.js (Vercel)    │         │  FastAPI + Uvicorn   │        │  PostgreSQL 15     │
│  React · Tailwind    │ ◄────── │  Alembic al arrancar │ ◄───── │  Session Pooler    │
│  Axios · Recharts    │  JSON   │                      │        │                    │
└──────────────────────┘         └──────────────────────┘        └────────────────────┘
         │                                  ▲
         │  Cookie httpOnly (JWT, SameSite=None; Secure)
         └──────────────────────────────────┘
```

### Arquitectura del backend: monolito en capas

Cada capa solo conoce a la inmediatamente inferior. Un router **nunca** toca la base de datos.

```
                     ┌─────────────────────────────────────────┐
   Petición HTTP ──► │  routers/                               │
                     │  Rutas, códigos de estado, validación   │
                     │  de entrada. Sin SQL, sin negocio.      │
                     └───────────────────┬─────────────────────┘
                                         │  Depends()
                     ┌───────────────────▼─────────────────────┐
                     │  services/                              │
                     │  REGLAS DE NEGOCIO. Fórmula del score,  │
                     │  analítica, límite transaccional.       │
                     │  Lanza excepciones de dominio.          │
                     └───────────────────┬─────────────────────┘
                                         │  Depends()
                     ┌───────────────────▼─────────────────────┐
                     │  repositories/                          │
                     │  ÚNICO punto que ejecuta SQL.           │
                     │  Aísla SQLAlchemy del resto.            │
                     └───────────────────┬─────────────────────┘
                                         │
                     ┌───────────────────▼─────────────────────┐
                     │  models/          │  PostgreSQL         │
                     │  Tablas SQLAlchemy                      │
                     └─────────────────────────────────────────┘

   Transversales:  core/ (config, seguridad, sesión de BD, dependencias)
                   schemas/ (contratos Pydantic de entrada y salida)
```

**Por qué monolito en capas y no microservicios ni hexagonal:** para el alcance de este dominio, los microservicios añaden complejidad de despliegue y orquestación sin beneficio real, y una arquitectura hexagonal pura sería sobreingeniería. El monolito en capas es el estándar profesional para APIs de este tamaño: separa responsabilidades, es testeable y es mantenible.

**Reglas que hacen que las capas se sostengan:**

- Los repositorios hacen `flush()` pero **nunca** `commit()`. El límite transaccional pertenece al servicio, porque solo él sabe dónde empieza y acaba una operación de negocio.
- Los servicios lanzan excepciones de dominio (`NotFoundError`, `ConflictError`), nunca `HTTPException`. `main.py` las traduce a códigos HTTP. Así un servicio se puede ejecutar desde un script o una tarea programada sin arrastrar FastAPI.
- Toda consulta de datos de usuario filtra por `user_id` **dentro del WHERE**, no en una comprobación posterior en Python. El aislamiento entre usuarios se garantiza en la capa de datos.

### Estructura del proyecto

```
sleep_metrics/
├── db/
│   └── schema.sql                    # Documentación de referencia del modelo
├── backend/
│   ├── alembic/
│   │   ├── env.py                    # Inyecta DATABASE_URL, expone Base.metadata
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── app/
│   │   ├── core/                     # config, database, security, dependencies
│   │   ├── models/                   # Tablas SQLAlchemy
│   │   ├── schemas/                  # Contratos Pydantic
│   │   ├── repositories/             # Acceso a datos (único SQL)
│   │   ├── services/                 # Lógica de negocio
│   │   ├── routers/                  # Endpoints HTTP
│   │   └── main.py                   # Ensamblado, CORS, manejo de errores
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── render.yaml                   # Infraestructura como código (opcional)
│   ├── start.sh                      # Migraciones + arranque del servidor
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── login/                # Login y registro con conmutador
    │   │   └── (app)/                # Área privada (grupo de rutas)
    │   │       ├── dashboard/
    │   │       ├── sessions/
    │   │       └── habits/
    │   ├── components/               # ui/ layout/ auth/ dashboard/ sessions/ habits/
    │   ├── context/AuthContext.tsx
    │   ├── lib/                      # api.ts (Axios), services.ts, format.ts
    │   └── types/api.ts
    ├── tailwind.config.ts
    └── .env.example
```

---

## El algoritmo de scoring

Implementado en [`backend/app/services/scoring_service.py`](backend/app/services/scoring_service.py) como lógica **pura**: recibe entidades y devuelve un resultado, sin tocar base de datos ni HTTP.

```
SCORE = DURACIÓN (40 pts) + INTERRUPCIONES (30 pts) + HÁBITOS (30 pts)
```

### 1. Duración — 40 puntos

Meseta plana en el rango óptimo de 7–9 h, con caídas lineales simétricas que agotan el componente a 3 horas de distancia del rango.

```
h ∈ [7, 9]   →  40 puntos
h < 7        →  40 × (1 − (7 − h) / 3)     acotado en [0, 40]
h > 9        →  40 × (1 − (h − 9) / 3)     acotado en [0, 40]
```

| Horas | 4 | 5 | 6 | 7–9 | 10 | 12 |
|---|---|---|---|---|---|---|
| **Puntos** | 0 | 13,33 | 26,67 | **40** | 26,67 | 0 |

Se penaliza el exceso igual que el defecto porque la hipersomnia se asocia con peor calidad de descanso, no con mejor.

### 2. Interrupciones — 30 puntos

```
puntos = max(0, 30 − 7,5 × nº de despertares)
```

| Despertares | 0 | 1 | 2 | 3 | ≥4 |
|---|---|---|---|---|---|
| **Puntos** | **30** | 22,5 | 15 | 7,5 | 0 |

Penalización lineal y no exponencial: el salto de 0 a 1 despertar no es cualitativamente distinto del de 2 a 3.

### 3. Hábitos — 30 puntos

#### 3a. Cafeína tardía (15 pts)

El impacto de la cafeína depende de **dos** variables, no de una: cuánta y cuánto falta para dormir. La vida media de la cafeína ronda las 5–6 horas, así que 200 mg a las 9:00 son irrelevantes mientras que los mismos 200 mg a las 21:00 arruinan la noche.

```
factor_cantidad   = min(1, mg / 400)
horas_antes       = sleep_start − hora_del_último_consumo
factor_proximidad = clamp((8 − horas_antes) / 8, 0, 1)

puntos = 15 − 15 × factor_cantidad × factor_proximidad
```

400 mg es el límite diario que las agencias de seguridad alimentaria consideran seguro para un adulto sano. 8 horas es la ventana tras la cual queda aproximadamente un 25 % de la dosis en el organismo.

| Escenario | Puntos |
|---|---|
| Sin cafeína | 15,00 |
| 200 mg, 10 h antes | 15,00 (fuera de ventana) |
| 200 mg, 4 h antes | 11,25 |
| 400 mg, 2 h antes | 3,75 |
| 400 mg, al acostarse | 0,00 |

Si no se conoce la hora del consumo se aplica un factor de proximidad de 0,5 (equivalente a 4 h antes): un punto medio que ni premia ocultar el dato ni castiga a quien no lo anotó.

#### 3b. Tiempo de pantalla antes de dormir (15 pts)

```
min ≤ 30    →  15 puntos
min ≥ 120   →   0 puntos
intermedio  →  15 × (1 − (min − 30) / 90)
```

| Minutos | 20 | 30 | 60 | 90 | ≥120 |
|---|---|---|---|---|---|
| **Puntos** | 15 | **15** | 10 | 5 | 0 |

> **Nota sobre `exercise_minutes`:** se registra y se muestra, pero **no entra en el score**. La especificación del componente de hábitos menciona expresamente cafeína y tiempo de pantalla; añadir el ejercicio por cuenta propia cambiaría la fórmula acordada. Queda disponible como dato para una versión futura.

### Caso sin hábitos registrados

Si no hay registro de hábitos para la fecha de la sesión, el 30 % no se puede evaluar. Dar 0 puntos castigaría al usuario por no rellenar un formulario; dar los 30 completos regalaría un score inflado. La solución correcta es reescalar sobre lo disponible:

```
SCORE = (duración + interrupciones) / 70 × 100
```

La respuesta incluye `habits_available: false` para que la interfaz avise de que el score es parcial.

### Emparejamiento sesión ↔ hábitos: la regla de la noche

Una sesión pertenece a la **noche del día en que empezó la velada**, no al día del reloj:

```
sleep_start a las 12:00 o más tarde  →  la noche de ESE día
sleep_start antes de las 12:00       →  la noche del día ANTERIOR

Viernes 23:30  →  noche del viernes
Sábado  00:05  →  noche del viernes
Sábado  23:30  →  noche del sábado
```

La regla vive en [`app/services/night.py`](backend/app/services/night.py) y la comparten el scoring, los hábitos y la analítica, para que exista una única definición.

**Por qué no basta con usar la fecha de `sleep_start`.** Funciona mientras uno se acueste antes de medianoche y se rompe en cuanto la cruza: dormirse a las 00:05 del sábado se registraba como sábado, pero el café y las pantallas que arruinaron esa noche eran los del **viernes**. El usuario tenía que anotarlos bajo una fecha que no correspondía con el día que había vivido. Peor aún, dos noches consecutivas podían reclamar la misma fecha —dormirse a las 00:05 del sábado y luego a las 23:30 del sábado— y disputarse un único registro de hábitos.

Con la regla del mediodía, cada franja de 24 horas de mediodía a mediodía contiene exactamente una noche, así que la colisión es imposible por construcción. El corte se sitúa en las 12:00 porque es el punto más alejado de cualquier hora plausible de acostarse: ninguna decisión real cae cerca del límite.

La interfaz refuerza la convención en lugar de esperar que el usuario la deduzca: al registrar una sesión se muestra en vivo *"cuenta como la noche del 14 ago"*, y el formulario de hábitos pide **"Noche del"** con el tramo que cubre.

---

## Modelo de datos

```
┌──────────────────────┐
│ users                │
│──────────────────────│
│ id          BIGINT PK│──────┐
│ name        VARCHAR  │      │
│ email       VARCHAR U│      │
│ password_hash VARCHAR│      │
│ created_at  TIMESTAMP│      │
└──────────────────────┘      │
                              │ ON DELETE CASCADE
        ┌─────────────────────┴──────────────────────┐
        │                                            │
┌───────▼──────────────────┐            ┌────────────▼──────────────────────────┐
│ sleep_sessions           │            │ daily_habits                          │
│──────────────────────────│            │───────────────────────────────────────│
│ id            BIGINT  PK │            │ id                        BIGINT   PK │
│ user_id       BIGINT  FK │            │ user_id                   BIGINT   FK │
│ sleep_start   TIMESTAMP  │            │ date                      DATE        │
│ sleep_end     TIMESTAMP  │            │ caffeine_mg               INTEGER     │
│ interruptions INTEGER    │            │ last_caffeine_time        TIME    NULL│
│ notes         TEXT       │            │ exercise_minutes          INTEGER     │
│ created_at    TIMESTAMP  │            │ screen_time_before_bed_.. INTEGER     │
└───────┬──────────────────┘            │ created_at                TIMESTAMP   │
        │                               │ UNIQUE (user_id, date)                │
        │ 1:1                           └───────────────────────────────────────┘
┌───────▼──────────────────┐
│ sleep_scores             │      Índices:
│──────────────────────────│        ix_sleep_sessions_user_id
│ id            BIGINT  PK │        ix_sleep_sessions_user_id_sleep_start (DESC)
│ session_id    BIGINT FK U│        ix_daily_habits_user_id
│ score         NUMERIC(5,2)        ix_daily_habits_date
│ calculated_at TIMESTAMP  │        ix_sleep_scores_session_id
└──────────────────────────┘
```

**Dos decisiones que conviene señalar:**

1. **`daily_habits.last_caffeine_time` no estaba en la especificación original.** Se añadió porque el algoritmo debe penalizar la *cafeína tardía*, y eso es imposible de calcular conociendo solo la cantidad diaria total. Es `NULL`-able porque el usuario puede no recordar la hora.

2. **`UNIQUE (user_id, date)` en `daily_habits`.** Es la restricción que da a `POST /habits` semántica de *upsert*: el usuario completa los datos del día de forma incremental (el café de la mañana antes que el tiempo de pantalla de la noche), así que volver a enviarlos debe actualizar, no duplicar.

El script [`db/schema.sql`](db/schema.sql) documenta el modelo completo con comentarios. **La fuente de verdad real del esquema son las migraciones de Alembic**, generadas a partir de los modelos SQLAlchemy.

---

## API

Base URL local: `http://localhost:8000` · Documentación interactiva en `/docs` (deshabilitada en producción).

| Método | Ruta | Auth | Descripción |
|---|---|:--:|---|
| `POST` | `/auth/register` | – | Crea cuenta y emite la cookie de sesión |
| `POST` | `/auth/login` | – | Valida credenciales y emite la cookie |
| `POST` | `/auth/demo` | – | Crea una cuenta de demostración sembrada y entra |
| `GET` | `/auth/me` | ✓ | Usuario de la sesión actual |
| `POST` | `/auth/logout` | – | Borra la cookie de sesión |
| `GET` | `/sessions` | ✓ | Historial paginado del usuario |
| `POST` | `/sessions` | ✓ | Registra una sesión y calcula su score |
| `GET` | `/sessions/{id}` | ✓ | Detalle de una sesión |
| `DELETE` | `/sessions/{id}` | ✓ | Elimina una sesión (score en cascada) |
| `POST` | `/habits` | ✓ | Registra o actualiza los hábitos de un día |
| `GET` | `/habits` | ✓ | Historial de hábitos |
| `GET` | `/analytics/summary` | ✓ | Medias, mejor/peor día, correlaciones |
| `GET` | `/analytics/score/{session_id}` | ✓ | Recalcula el score con su desglose |
| `GET` | `/health` | – | Estado de la API y de la base de datos |

### Dos endpoints añadidos a la especificación original

`GET /auth/me` y `POST /auth/logout` **no** estaban en el listado inicial. Son consecuencia obligada de haber elegido cookies httpOnly: el JavaScript del frontend no puede leer la cookie ni decodificar el JWT, así que necesita preguntar al backend quién es el usuario; y tampoco puede borrar una cookie httpOnly, de modo que el cierre de sesión debe ordenarlo el servidor con una cabecera `Set-Cookie`.

### Ejemplo: desglose de un score

```http
GET /analytics/score/42
```

```json
{
  "session_id": 42,
  "score": 66.25,
  "calculated_at": "2026-08-15T09:12:04",
  "duration_hours": 8.0,
  "habits_available": true,
  "components": [
    { "name": "Duracion",           "points": 40.0, "max_points": 40.0,
      "detail": "8.0 h de sueno, dentro del rango optimo (7-9 h)." },
    { "name": "Interrupciones",     "points": 22.5, "max_points": 30.0,
      "detail": "1 despertar: -7.5 puntos." },
    { "name": "Cafeina",            "points":  3.75, "max_points": 15.0,
      "detail": "400 mg de cafeina, ultimo consumo 2.0 h antes de dormir: -11.2 puntos." },
    { "name": "Tiempo de pantalla", "points":  0.0, "max_points": 15.0,
      "detail": "150 min de pantalla antes de dormir: -15.0 puntos." }
  ]
}
```

---

## Capturas

> Reemplazar por capturas reales tras el despliegue.

| Pantalla | Captura |
|---|---|
| Login / registro | `docs/screenshots/login.png` |
| Panel principal | `docs/screenshots/dashboard.png` |
| Registro de sesión | `docs/screenshots/new-session.png` |
| Historial | `docs/screenshots/history.png` |
| Hábitos diarios | `docs/screenshots/habits.png` |

---

## Ejecutar en local

### Requisitos

- Python 3.11
- Node.js 18 o superior
- Una base de datos PostgreSQL (Supabase, una instalación local, o Docker)

### 1. Base de datos

**Opción A — Supabase** (la misma que se usa en producción): ver [Crear el proyecto en Supabase](#paso-1-crear-el-proyecto-en-supabase).

**Opción B — PostgreSQL con Docker:**

```bash
docker run -d --name sleepmetrics-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=sleepmetrics \
  -p 5432:5432 postgres:16-alpine
```

### 2. Backend

```bash
cd backend

# Entorno virtual
python -m venv venv
source venv/bin/activate          # Linux / macOS
venv\Scripts\activate             # Windows

pip install -r requirements.txt

# Configuración
cp .env.example .env              # Windows: Copy-Item .env.example .env
```

Edita `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/sleepmetrics
JWT_SECRET_KEY=<genera uno, ver más abajo>
CORS_ORIGINS=http://localhost:3000
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

Genera un secreto de firma:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Aplica las migraciones y arranca:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

API en `http://localhost:8000` · documentación en `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install

cp .env.example .env.local        # Windows: Copy-Item .env.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

Aplicación en `http://localhost:3000`.

> **Sobre las cookies en desarrollo:** `localhost:3000` y `localhost:8000` se consideran el mismo *site* (el puerto no cuenta para `SameSite`), por lo que `COOKIE_SAMESITE=lax` y `COOKIE_SECURE=false` funcionan sin HTTPS. En producción los valores son distintos, ver la sección de despliegue.

---

## Migraciones de base de datos

Alembic es la herramienta estándar del ecosistema SQLAlchemy y trata a Supabase simplemente como una base de datos PostgreSQL más: se conecta con la misma cadena de conexión, sin necesitar su SDK.

Todos los comandos se ejecutan desde `backend/` con el entorno virtual activo.

### Aplicar migraciones pendientes

```bash
alembic upgrade head
```

Es idempotente: compara la tabla `alembic_version` con las revisiones disponibles y aplica solo lo que falte.

### Generar una migración tras cambiar un modelo

```bash
# 1. Editas el modelo en app/models/
# 2. Alembic compara los modelos con la base de datos real
alembic revision --autogenerate -m "add sleep_quality_notes column"

# 3. REVISA el archivo generado en alembic/versions/ antes de aplicarlo
# 4. Aplica
alembic upgrade head
```

> **Revisa siempre el archivo generado.** El autogenerado de Alembic detecta muy bien columnas, índices y restricciones, pero no adivina intenciones: un renombrado de columna lo interpreta como un `DROP` seguido de un `ADD`, lo que borraría los datos de esa columna.

### Otros comandos útiles

```bash
alembic current                   # Revisión aplicada actualmente
alembic history --verbose         # Historial completo
alembic downgrade -1              # Revierte la última migración
alembic check                     # ¿Hay cambios en los modelos sin migrar?
alembic upgrade head --sql        # Genera el SQL sin ejecutarlo (revisión en PR)
```

### Registrar un modelo nuevo

Al añadir un modelo hay que importarlo en [`app/models/__init__.py`](backend/app/models/__init__.py). Alembic construye las migraciones a partir de `Base.metadata`, y una tabla solo aparece ahí si su módulo llegó a ejecutarse. Si se olvida, el autogenerado no verá la tabla nueva y, peor aún, interpretará las existentes que no encuentre como sobrantes.

### Aplicación automática en producción

Las migraciones se aplican **antes** de que el servidor acepte la primera petición, mediante [`backend/start.sh`](backend/start.sh), que es el *Start Command* del servicio en Render:

```bash
set -euo pipefail
alembic upgrade head                     # Si falla, el despliegue se aborta
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
```

**Por qué un script y no el evento `lifespan` de FastAPI:**

1. **Concurrencia.** Render puede arrancar varias instancias, o solapar la antigua y la nueva durante un despliegue. Si cada proceso migrara en su propio `lifespan`, competirían por el mismo lock de Alembic. Un paso previo y separado ocurre una sola vez por despliegue.
2. **Diagnóstico.** Con `set -e`, una migración fallida aborta el arranque y Render marca el despliegue como fallido, con el error visible en el log. Dentro del `lifespan` el fallo quedaría sepultado y el servicio podría acabar sirviendo tráfico contra un esquema incorrecto.

---

## Despliegue

### Paso 1: Crear el proyecto en Supabase

1. Entra en [supabase.com](https://supabase.com) y crea una cuenta.
2. **New project**. Elige nombre, **genera y guarda la contraseña de la base de datos** (no se vuelve a mostrar) y selecciona la región más cercana a la de tu servicio de Render.
3. Espera a que termine el aprovisionamiento (1–2 minutos).
4. Ve a **Project Settings → Database → Connection string** y selecciona la pestaña **Session pooler**.
5. Copia la cadena, que tiene esta forma:

   ```
   postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
   ```

6. Sustituye `[YOUR-PASSWORD]` por la contraseña del paso 2 y adapta el prefijo para SQLAlchemy:

   ```
   postgresql+psycopg2://postgres.abcdefghijklmnop:TU_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```

> #### Usa el Session Pooler, no la conexión directa
>
> Esto es lo que más despliegues rompe, así que conviene entenderlo:
>
> - **Conexión directa** (`db.<ref>.supabase.co`): en los proyectos nuevos resuelve **solo a IPv6**, y la red saliente del plan gratuito de Render es IPv4. La conexión fallaría con un error de red difícil de diagnosticar.
> - **Transaction pooler** (puerto `6543`): usa PgBouncer en modo transacción, que no mantiene estado a nivel de sesión. Las migraciones de Alembic lo necesitan (locks, sentencias preparadas, DDL transaccional).
> - **Session pooler** (puerto `5432`): compatible con IPv4 **y** conserva el estado de sesión. Es la opción correcta.
>
> Si tu contraseña contiene `@ : / ? # [ ] %`, codifícala en *percent-encoding* (`p@ss` → `p%40ss`).

**No hace falta ejecutar `db/schema.sql`.** El backend aplica las migraciones de Alembic automáticamente al arrancar. Ese archivo es documentación de referencia. Si aun así decides ejecutarlo a mano, marca después la revisión como aplicada para evitar un doble `CREATE TABLE`:

```bash
alembic stamp 0001_initial_schema
```

### Paso 2: Desplegar el backend en Render

1. Sube el repositorio a GitHub.
2. En [render.com](https://render.com): **New + → Web Service** y conecta el repositorio.
3. Configura:

   | Campo | Valor |
   |---|---|
   | Name | `sleepmetrics-api` |
   | Region | La misma que elegiste en Supabase |
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `bash start.sh` |
   | Instance Type | Free |
   | Health Check Path | `/health` |

4. En **Environment**, añade estas variables:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | La cadena del Session Pooler del paso 1 |
   | `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `ENVIRONMENT` | `production` |
   | `CORS_ORIGINS` | *(pendiente: la URL de Vercel, se rellena en el paso 4)* |
   | `COOKIE_SECURE` | `true` |
   | `COOKIE_SAMESITE` | `none` |
   | `PYTHON_VERSION` | `3.11.9` |

5. **Create Web Service**. En el log de despliegue deberías ver:

   ```
   ==> Aplicando migraciones de base de datos (alembic upgrade head)...
   INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema
   ==> Migraciones aplicadas correctamente.
   ==> Levantando servidor uvicorn en el puerto 10000...
   ```

6. Comprueba que responde: `https://sleepmetrics-api.onrender.com/health` debe devolver `{"api":"ok","database":"ok"}`.

> Como alternativa al alta manual, el repositorio incluye [`backend/render.yaml`](backend/render.yaml): **New + → Blueprint** lee esa definición y crea el servicio ya configurado.

### Paso 3: Desplegar el frontend en Vercel

1. En [vercel.com](https://vercel.com): **Add New → Project** e importa el repositorio.
2. Configura:

   | Campo | Valor |
   |---|---|
   | Framework Preset | Next.js |
   | Root Directory | `frontend` |

3. En **Environment Variables**:

   | Variable | Valor |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://sleepmetrics-api.onrender.com` *(sin barra final)* |

4. **Deploy**. Anota la URL resultante, por ejemplo `https://sleepmetrics.vercel.app`.

### Paso 4: Cerrar el círculo del CORS

Vuelve a Render y actualiza `CORS_ORIGINS` con la URL exacta de Vercel:

```
CORS_ORIGINS=https://sleepmetrics.vercel.app
```

Render redesplegará automáticamente. **Este paso no es opcional:** sin él, el navegador bloqueará todas las peticiones y la aplicación no podrá ni iniciar sesión.

> El valor debe ser el origen **exacto**, sin barra final. No se admite `*`: la especificación de CORS lo prohíbe cuando se permiten credenciales, y aquí son imprescindibles porque la sesión viaja en una cookie.

### Verificación final

1. Abre la URL de Vercel.
2. Crea una cuenta. En las herramientas de desarrollo, pestaña **Application → Cookies**, debe aparecer `sleepmetrics_access_token` con las marcas `HttpOnly`, `Secure` y `SameSite=None`.
3. Registra una sesión de sueño y comprueba que aparece el score.
4. Registra los hábitos de ese mismo día y verifica que el score se recalcula.
5. Recarga la página: la sesión debe mantenerse.

### Limitaciones conocidas del plan gratuito

- **Arranque en frío de Render.** El servicio se suspende tras 15 minutos sin tráfico y el siguiente acceso tarda unos 50 segundos. Por eso el cliente de Axios usa un timeout de 30 s y muestra un mensaje específico. Se puede mitigar con un cron externo (por ejemplo [cron-job.org](https://cron-job.org)) que haga ping a `/health` cada 10 minutos.
- **Pausa de Supabase.** Los proyectos gratuitos se pausan tras 7 días de inactividad y hay que reactivarlos desde el panel.
- **Cookies de terceros.** La cookie de sesión es *cross-site* (`vercel.app` → `onrender.com`). Los navegadores están restringiendo progresivamente las cookies de terceros; si eso llegara a afectar al despliegue, la solución es servir ambos bajo un mismo dominio registrable (por ejemplo `app.tudominio.com` y `api.tudominio.com`), lo que convertiría la cookie en *same-site* y permitiría usar `SameSite=Lax`.

---

## Decisiones técnicas

### Autenticación en cookie httpOnly y no en localStorage

El JWT viaja en una cookie `httpOnly`, inaccesible desde JavaScript. Es la diferencia entre un XSS que roba la sesión y un XSS que no puede tocarla.

El coste de esa decisión es real y se asume de forma explícita:

- Obliga a `withCredentials: true` en Axios y a `allow_credentials=True` con orígenes exactos en el CORS del backend.
- Requiere `SameSite=None; Secure` en producción, al ser dominios distintos.
- Añade dos endpoints (`/auth/me` y `/auth/logout`) que con localStorage no harían falta.
- La protección de rutas se resuelve en el cliente y no en el middleware de Next.js: la cookie la emite el dominio del backend, así que el servidor de Vercel nunca la recibe. **Eso no es un problema de seguridad**, porque la barrera real es el backend, que exige un JWT válido en cada endpoint; el guardián del frontend es solo comodidad de navegación.

**CSRF:** `SameSite=None` reabre en teoría esa puerta. Está mitigado porque todos los endpoints que modifican estado consumen `application/json`, un `Content-Type` que obliga al navegador a lanzar un *preflight* `OPTIONS` que CORS rechaza para cualquier origen no autorizado. Un formulario HTML malicioso no puede emitir ese `Content-Type`.

### El score se persiste, no se calcula siempre al vuelo

`sleep_scores` guarda el resultado por dos razones: el historial y el panel necesitan el score de decenas de sesiones en una sola consulta (`JOIN`) sin recalcular cada una, y `calculated_at` deja trazabilidad.

Para evitar que el valor se quede obsoleto, se recalcula en los dos momentos en que puede cambiar: al llamar a `GET /analytics/score/{id}` y al guardar los hábitos de un día (que actualiza el score de la noche correspondiente).

### `TIMESTAMP` sin zona horaria

El dominio del sueño es **local** por naturaleza: «me acosté a las 23:30» significa las 23:30 donde está el usuario, no un instante absoluto en UTC. Guardar con zona obligaría a conocer el huso de cada usuario para volver a mostrar el dato correctamente.

La consecuencia asumida es que las ventanas de «últimos 7 días» de la analítica se calculan con la hora del servidor, de modo que un usuario en un huso muy alejado podría ver una sesión entrar o salir de la ventana por unas horas. Manejarlo con precisión exigiría almacenar la zona horaria de cada usuario, algo fuera del alcance actual.

### Pearson implementado a mano

La correlación se calcula con aritmética estándar de Python en lugar de traer NumPy o SciPy: son dependencias de decenas de megabytes para una fórmula de cinco líneas, y el plan gratuito de Render tiene límites estrechos de memoria y de tiempo de compilación.

Se exigen al menos 5 pares de datos para devolver un coeficiente. Con 2 o 3 puntos, casi cualquier nube de datos produce una correlación cercana a ±1 por puro azar; devolver `null` es más honesto que devolver un número sin respaldo.

### `bcrypt` fijado a la serie 4.0.x

`passlib` 1.7.4 lee el atributo `bcrypt.__about__` para detectar la versión del backend, y ese atributo desapareció en `bcrypt` 4.1. Con versiones más nuevas, `passlib` emite un error ruidoso en cada arranque. Fijar `bcrypt==4.0.1` lo evita.

Además, `bcrypt` trunca en silencio cualquier entrada de más de 72 **bytes**. El límite se valida en los schemas Pydantic (en bytes UTF-8, no en caracteres) para que el usuario reciba un error claro en lugar de una truncación invisible que debilitaría su contraseña.

### La demostración da una cuenta aislada a cada visitante

El botón **"Probar sin registrarme"** del login llama a `POST /auth/demo`, que crea una cuenta desechable **propia de ese visitante**, la siembra con 45 días de historial ficticio y emite la cookie de sesión. Sin formulario, sin credenciales.

El patrón habitual en un portafolio —una única cuenta de demostración con credenciales públicas— tiene un fallo que no se puede tapar: todos los visitantes escriben sobre los mismos datos. Basta con que uno borre el historial para que el siguiente encuentre la aplicación vacía, y dos personas simultáneas se pisan los cambios en tiempo real.

Se descartaron dos alternativas antes de llegar aquí:

- **Borrado ilusorio** (que el `DELETE` no borre de verdad en la cuenta de demostración): se rompe al recargar la página, y obliga a que la API mienta devolviendo `204` sin haber hecho nada.
- **Re-sembrar al iniciar sesión**: no resuelve la concurrencia, solo la mueve de sitio. El segundo visitante le borra los datos al primero en mitad de su prueba.

Con una cuenta por visitante, la aplicación funciona **al 100 %**: crear, editar y borrar de verdad, sin restricciones ni simulaciones. Nadie puede estropearle la prueba a nadie.

El coste son cuentas acumuladas, controlado por dos vías que se ejecutan antes de crear cada cuenta nueva: **caducidad** (se eliminan las de más de `DEMO_ACCOUNT_TTL_HOURS`) y **tope** (nunca más de `DEMO_ACCOUNT_MAX_ACTIVE` vivas, como protección frente a un bot). El `ON DELETE CASCADE` se lleva sesiones, hábitos y scores. Además, `start.sh` ejecuta `python -m scripts.purge_demo_accounts` en cada despliegue, para el caso de que el portafolio pase semanas sin visitas y la limpieza perezosa nunca llegue a dispararse.

`users.is_demo` es una columna real y no una deducción a partir del dominio del email: una comparación de cadenas sería frágil y no se podría indexar. Lleva un **índice parcial** (`WHERE is_demo`), que es lo correcto para una columna booleana tan sesgada — las cuentas reales, que son la inmensa mayoría, nunca se consultan por ella.

#### Los datos ficticios modelan causalidad, no ruido

El generador no sortea valores al azar: si lo hiciera, las correlaciones saldrían nulas y el "mejor día de la semana" no significaría nada, que es justo la parte del proyecto que merece la pena enseñar.

Dos ajustes que costaron una iteración cada uno, detectados por los tests:

1. **La cafeína no depende del día de la semana.** Una primera versión daba más cafeína entre semana, lo que parecía más realista; pero entre semana también se duerme mejor (menos pantallas, menos interrupciones), así que el día de la semana actuaba como variable de confusión y la correlación salía **positiva**: el panel afirmaba "cuanta más cafeína, mejor descansas".

2. **Los hábitos alteran la noche, no solo el score.** Con duración e interrupciones sorteadas de forma independiente, su variabilidad —que mueve hasta 70 de los 100 puntos— ahogaba la señal de la cafeína, dejando el coeficiente en −0,13, por debajo del umbral en el que la aplicación lo considera apreciable. La solución fue modelar el efecto fisiológico real: la cafeína tardía **también** acorta el sueño y multiplica los despertares en los datos generados. Eso no es maquillar cifras — es lo que hace que la correlación que muestra la aplicación se corresponda con una causa presente en el historial. **La fórmula del score no se toca en ningún momento.**

3. **El historial dura 90 días, no 45, y eso es estadística y no capricho.** Con 45 días quedaban unas 30 muestras útiles, y con esa cantidad el coeficiente de Pearson sobre un predictor discreto como los miligramos de cafeína oscilaba entre **−0,60 y +0,07 solo cambiando la semilla** del generador: la calidad de la demostración dependía de la suerte. Antes de fijar el valor se barrieron diez semillas distintas midiendo correlaciones y separación entre días; a 45 días fallaban 3 de 10, a 90 no falla ninguna.

Resultado con las diez semillas probadas: correlación de cafeína entre **−0,32 y −0,66**, tiempo de pantalla entre **−0,37 y −0,70** (ambas "relación inversa moderada" o mejor), y entre 7 y 21 puntos de diferencia entre el mejor y el peor día de la semana.

El generador produce además horas de acostarse **a ambos lados de medianoche**, lo que ejercita la regla de la noche con datos reales en cada cuenta de demostración.

### Navegación responsive: una sola definición, dos presentaciones

El punto de corte es `md` (768 px). En escritorio, la barra lateral es un elemento fijo de 256 px; por debajo, se sustituye por una cabecera fija con botón de menú y la misma barra entra deslizándose sobre un fondo oscurecido.

`AppShell` reutiliza el componente `Sidebar` en ambos casos en lugar de mantener una navegación móvil aparte: dos navegaciones distintas acaban divergiendo en cuanto se añade una pantalla a una y se olvida en la otra.

Dos detalles del *drawer* que merecen mención:

- **Se oculta con `visibility: hidden`, no con `opacity` ni desplazándolo fuera de pantalla.** Es lo que saca a sus descendientes del orden de tabulación. Con las otras dos técnicas, los enlaces del menú cerrado seguirían siendo enfocables con el tabulador, atrapando a quien navega con teclado en un menú invisible. Además es una propiedad transicionable, así que la animación de entrada se conserva.
- **Implementa el contrato completo de diálogo modal:** bloqueo del scroll de fondo, cierre con `Escape` y al pulsar el fondo, confinamiento del foco en ciclo dentro del panel y devolución del foco al botón que lo abrió. Sin el confinamiento, el `aria-modal="true"` sería una declaración falsa: el tabulador saldría hacia un contenido que visualmente está tapado.

#### Las tablas y el bug de `min-width: auto`

Los historiales de sesiones y de hábitos conservan su ancho mínimo y se desplazan horizontalmente **dentro de su propio contenedor** (`overflow-x-auto`), de modo que la página nunca hace scroll lateral.

Ese patrón es habitual, pero fallaba de una forma instructiva: **en la página de hábitos desbordaba la pantalla entera y la tabla no llegaba a desplazarse.**

La causa está en la especificación de CSS Grid y Flexbox. Un elemento de grid tiene `min-width: auto`, que resuelve a su ancho **min-content**. La `Card` que contenía la tabla era un elemento de grid, así que su mínimo pasaba a ser los 720 px de la tabla: la columna se estiraba hasta ahí y arrastraba la página fuera del viewport. El `overflow-x-auto` interior no podía evitarlo, porque **la restricción la imponía un ancestro, no el contenedor que se desplaza** — la regla que reduce ese mínimo automático a 0 se aplica al elemento que lleva el `overflow`, no a sus descendientes.

La corrección es `min-w-0` en `Card`, que anula el mínimo automático y devuelve el control al contenedor con scroll. Se aplica por defecto en el componente y no caso por caso: las tarjetas se usan casi siempre dentro de un grid o un flex, así que el valor seguro debe ser el que traen de serie. Los campos `Input` llevan la misma protección, porque `datetime-local`, `date` y `time` tienen anchos intrínsecos grandes y reproducen el mismo fallo.

### Estado de verificación

El proyecto se ha validado contra PostgreSQL real:

- `alembic upgrade head` aplica el esquema limpio y `alembic check` no detecta deriva entre los modelos y la migración.
- 43 comprobaciones de integración sobre la API cubren registro, emisión de cookie `HttpOnly`, aislamiento entre usuarios (un usuario recibe 404 al pedir recursos de otro), la fórmula del score en sus casos límite, el recálculo al guardar hábitos, la semántica de upsert y el borrado en cascada.
- 37 comprobaciones más sobre las cuentas de demostración: siembra, calidad estadística de los datos generados, aislamiento real entre dos visitantes (uno borra su historial completo y el del otro queda intacto), aplicación del tope de cuentas vivas, y purga por caducidad con borrado en cascada sin filas huérfanas.
- El frontend compila sin errores de tipos (`next build`, 7 rutas).

No se incluye una suite de tests automatizada en el repositorio: se descartó de forma explícita durante la definición del alcance. Es la primera ampliación recomendada.

---

## Convenciones de commits

Formato semántico ([Conventional Commits](https://www.conventionalcommits.org/)). Secuencia sugerida para publicar el proyecto:

```
chore: scaffold del repositorio con gitignore y gitattributes
feat(db): esquema inicial de PostgreSQL como documentacion de referencia
feat(backend): configuracion, conexion a base de datos y primitivas de seguridad
feat(backend): modelos SQLAlchemy de usuarios, sesiones, habitos y scores
feat(backend): schemas Pydantic de entrada y salida de la API
feat(backend): capa de repositorios con acceso aislado a datos
feat(backend): algoritmo de scoring de calidad de sueno ponderado
feat(backend): servicios de autenticacion, sesiones, habitos y analitica
feat(backend): inyeccion de dependencias y extraccion del usuario autenticado
feat(api): endpoints de auth, sesiones, habitos y analitica
feat(backend): manejo centralizado de errores de dominio y CORS
feat(db): migracion inicial de Alembic y configuracion del entorno
chore(deploy): script de arranque con migraciones automaticas y blueprint de Render
feat(frontend): configuracion de Next.js, Tailwind y sistema de tokens de color
feat(frontend): cliente Axios con interceptores y normalizacion de errores
feat(frontend): contexto de autenticacion basado en cookie httpOnly
feat(frontend): componentes de interfaz reutilizables
feat(frontend): pantalla de acceso con conmutador entre login y registro
feat(frontend): panel con grafica de sueno, score y correlaciones
feat(frontend): registro de sesiones, historial y habitos diarios
fix(frontend): adapta el tooltip de la grafica a la API de Recharts 3
chore(deps): actualiza Next.js a 14.2.35 por parche de seguridad
feat(frontend): menu lateral deslizante en movil con foco confinado
feat(db): anade la marca is_demo a users con indice parcial
feat(backend): cuentas de demostracion aisladas y sembradas por visitante
fix(backend): desacopla la cafeina del dia de la semana en los datos de demo
feat(frontend): acceso de un clic a la demostracion y aviso de cuenta temporal
chore(deploy): purga de cuentas de demostracion caducadas en cada despliegue
feat(backend): regla de la noche para emparejar sesiones con habitos
fix(backend): estabiliza las correlaciones de la demo ampliando el historial a 90 dias
feat(frontend): muestra en vivo a que noche pertenece cada sesion
fix(frontend): corrige el desbordamiento horizontal por min-width auto en grid
docs: README con arquitectura, formula de scoring y guia de despliegue
```

---

## Licencia

MIT.
