-- ============================================================================
-- SleepMetrics - Esquema de base de datos (PostgreSQL 15+ / Supabase)
-- ============================================================================
--
-- PROPOSITO DE ESTE ARCHIVO
-- -------------------------
-- Este script es DOCUMENTACION DE REFERENCIA del modelo de datos. Sirve para
-- entender la estructura completa de un vistazo y para levantar la base de
-- datos manualmente desde el editor SQL de Supabase si se desea.
--
-- La FUENTE DE VERDAD del schema a lo largo del tiempo son las migraciones de
-- Alembic (backend/alembic/versions/), generadas a partir de los modelos
-- SQLAlchemy. Si ejecutas este script manualmente y luego corres Alembic,
-- marca la revision inicial como aplicada para evitar un doble CREATE TABLE:
--
--     alembic stamp 0001_initial_schema
--
-- El flujo recomendado es NO ejecutar este script y dejar que Alembic cree
-- todo (el backend aplica migraciones automaticamente al arrancar).
--
-- Convenciones:
--   - IDs con GENERATED ALWAYS AS IDENTITY (estandar SQL, sustituto de SERIAL)
--   - TIMESTAMP sin zona horaria: todas las marcas de tiempo se almacenan y se
--     interpretan como hora local del usuario. El dominio del sueno es
--     inherentemente local ("me dormi a las 23:30"), no absoluto.
--   - ON DELETE CASCADE: borrar un usuario elimina todo su historial.
-- ============================================================================


-- ============================================================================
-- LIMPIEZA (idempotencia al re-ejecutar el script en desarrollo)
-- El orden es inverso al de creacion por las dependencias de llave foranea.
-- ============================================================================
DROP TABLE IF EXISTS sleep_scores;
DROP TABLE IF EXISTS daily_habits;
DROP TABLE IF EXISTS sleep_sessions;
DROP TABLE IF EXISTS users;


-- ============================================================================
-- TABLA: users
-- Cuentas de la aplicacion. La autenticacion la gestiona el backend con JWT
-- propio; Supabase se usa unicamente como PostgreSQL administrado, por lo que
-- esta tabla NO tiene relacion alguna con el esquema auth.users de Supabase.
-- ============================================================================
CREATE TABLE users (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Nombre para mostrar en la interfaz.
    name          VARCHAR(120) NOT NULL,

    -- Identificador de login. UNIQUE crea implicitamente un indice btree, por
    -- lo que no hace falta declarar un indice adicional sobre esta columna.
    email         VARCHAR(255) NOT NULL UNIQUE,

    -- Hash bcrypt de la contrasena (nunca la contrasena en claro).
    -- bcrypt produce siempre 60 caracteres; 255 deja margen para migrar a
    -- otro algoritmo en el futuro sin alterar la tabla.
    password_hash VARCHAR(255) NOT NULL,

    -- Marca las cuentas desechables que crea POST /auth/demo: cada visitante
    -- del portafolio recibe la suya, sembrada con datos ficticios, y se
    -- elimina automaticamente pasadas 24 horas.
    is_demo       BOOLEAN      NOT NULL DEFAULT false,

    created_at    TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),

    -- El email se normaliza a minusculas en el backend antes de persistir;
    -- este CHECK garantiza la invariante tambien a nivel de base de datos y
    -- evita que dos cuentas difieran solo en mayusculas.
    CONSTRAINT ck_users_email_lowercase CHECK (email = lower(email))
);

-- Indice PARCIAL: solo cubre las filas de cuentas de demostracion.
-- La columna esta muy sesgada (casi todas las cuentas son reales) y solo se
-- consulta para localizar las de demostracion, asi que un indice completo
-- ocuparia espacio y encareceria cada alta sin aportar nada.
CREATE INDEX ix_users_is_demo ON users (is_demo) WHERE is_demo;

COMMENT ON TABLE  users IS 'Cuentas de usuario de SleepMetrics (auth propia con JWT)';
COMMENT ON COLUMN users.password_hash IS 'Hash bcrypt, generado por passlib en el backend';
COMMENT ON COLUMN users.is_demo IS 'Cuenta desechable de demostracion, purgada por antiguedad';


-- ============================================================================
-- TABLA: sleep_sessions
-- Una fila por noche registrada. Es la entidad central del dominio.
-- ============================================================================
CREATE TABLE sleep_sessions (
    id            BIGINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    user_id       BIGINT    NOT NULL
                            REFERENCES users (id) ON DELETE CASCADE,

    -- Momento en que el usuario se acosto / se durmio.
    sleep_start   TIMESTAMP NOT NULL,

    -- Momento en que el usuario desperto.
    sleep_end     TIMESTAMP NOT NULL,

    -- Numero de veces que se desperto durante la noche.
    interruptions INTEGER   NOT NULL DEFAULT 0,

    -- Notas libres opcionales ("dormi con ruido", "cena pesada", etc.).
    notes         TEXT,

    created_at    TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),

    -- Invariantes del dominio validadas tambien en la capa de servicios.
    -- Se replican aqui porque la base de datos es la ultima linea de defensa.
    CONSTRAINT ck_sleep_sessions_end_after_start
        CHECK (sleep_end > sleep_start),

    CONSTRAINT ck_sleep_sessions_interruptions_non_negative
        CHECK (interruptions >= 0),

    -- Una sesion de mas de 24 horas es casi con seguridad un error de captura.
    CONSTRAINT ck_sleep_sessions_max_duration
        CHECK (sleep_end <= sleep_start + INTERVAL '24 hours')
);

-- Indice sobre user_id: toda consulta del historial filtra por usuario.
CREATE INDEX ix_sleep_sessions_user_id ON sleep_sessions (user_id);

-- Indice compuesto para el patron de acceso dominante: "las sesiones del
-- usuario X ordenadas de mas reciente a mas antigua". DESC en la segunda
-- columna permite servir el ORDER BY directamente desde el indice.
CREATE INDEX ix_sleep_sessions_user_id_sleep_start
    ON sleep_sessions (user_id, sleep_start DESC);

COMMENT ON TABLE sleep_sessions IS 'Registro de cada noche de sueno de un usuario';


-- ============================================================================
-- TABLA: daily_habits
-- Habitos diurnos que influyen en la calidad del sueno de esa noche.
-- Una fila por usuario y dia.
-- ============================================================================
CREATE TABLE daily_habits (
    id                             BIGINT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    user_id                        BIGINT  NOT NULL
                                           REFERENCES users (id) ON DELETE CASCADE,

    -- Dia al que corresponden los habitos. Se asocia a la sesion de sueno cuyo
    -- sleep_start cae en esta misma fecha (la noche que comienza ese dia).
    date                           DATE    NOT NULL,

    -- Cafeina total consumida en el dia, en miligramos.
    caffeine_mg                    INTEGER NOT NULL DEFAULT 0,

    -- Hora del ULTIMO consumo de cafeina del dia.
    --
    -- NOTA DE DISENO: esta columna no estaba en la especificacion original,
    -- pero el algoritmo de scoring debe penalizar la "cafeina tardia" y eso es
    -- imposible de calcular conociendo unicamente la cantidad diaria total.
    -- Es NULL-able porque el usuario puede no recordar la hora: en ese caso el
    -- servicio de scoring aplica un factor de proximidad conservador.
    last_caffeine_time             TIME,

    exercise_minutes               INTEGER NOT NULL DEFAULT 0,

    -- Minutos de pantalla en la hora previa a acostarse.
    screen_time_before_bed_minutes INTEGER NOT NULL DEFAULT 0,

    created_at                     TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),

    -- Un unico registro de habitos por usuario y dia. Esta restriccion es la
    -- que permite que POST /habits tenga semantica de upsert (crear o
    -- actualizar) en lugar de acumular duplicados.
    CONSTRAINT uq_daily_habits_user_id_date UNIQUE (user_id, date),

    CONSTRAINT ck_daily_habits_caffeine_non_negative
        CHECK (caffeine_mg >= 0),

    CONSTRAINT ck_daily_habits_exercise_non_negative
        CHECK (exercise_minutes >= 0 AND exercise_minutes <= 1440),

    CONSTRAINT ck_daily_habits_screen_time_non_negative
        CHECK (screen_time_before_bed_minutes >= 0
               AND screen_time_before_bed_minutes <= 1440)
);

CREATE INDEX ix_daily_habits_user_id ON daily_habits (user_id);

-- Indice sobre date: el servicio de analytics agrega por rangos de fecha.
CREATE INDEX ix_daily_habits_date ON daily_habits (date);

COMMENT ON TABLE daily_habits IS 'Habitos diarios que alimentan el calculo del score de sueno';
COMMENT ON COLUMN daily_habits.last_caffeine_time IS 'Hora del ultimo consumo de cafeina; NULL si se desconoce';


-- ============================================================================
-- TABLA: sleep_scores
-- Score de calidad (0-100) calculado para cada sesion de sueno.
--
-- Se persiste en lugar de calcularse siempre al vuelo por dos razones:
--   1. El historial y el dashboard necesitan el score de decenas de sesiones
--      en una sola consulta (JOIN) sin recalcular cada una.
--   2. calculated_at deja trazabilidad de cuando se evaluo la sesion.
-- El endpoint GET /analytics/score/{id} recalcula y actualiza la fila, para
-- reflejar habitos registrados despues de haber creado la sesion.
-- ============================================================================
CREATE TABLE sleep_scores (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Relacion 1:1 con la sesion: UNIQUE garantiza un unico score vigente por
    -- sesion, de modo que el recalculo sea un UPDATE y nunca un INSERT extra.
    session_id    BIGINT       NOT NULL UNIQUE
                               REFERENCES sleep_sessions (id) ON DELETE CASCADE,

    -- NUMERIC en lugar de FLOAT: evita errores de redondeo binario al mostrar
    -- valores como 87.50 en la interfaz.
    score         NUMERIC(5,2) NOT NULL,

    calculated_at TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),

    CONSTRAINT ck_sleep_scores_range CHECK (score >= 0 AND score <= 100)
);

CREATE INDEX ix_sleep_scores_session_id ON sleep_scores (session_id);

COMMENT ON TABLE sleep_scores IS 'Score de calidad 0-100 calculado por el servicio de scoring';


-- ============================================================================
-- VERIFICACION
-- Ejecutar tras el script para confirmar que las cuatro tablas existen.
-- ============================================================================
-- SELECT table_name
--   FROM information_schema.tables
--  WHERE table_schema = 'public'
--  ORDER BY table_name;
