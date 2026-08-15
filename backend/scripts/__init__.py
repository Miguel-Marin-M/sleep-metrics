"""Scripts de mantenimiento ejecutables desde la linea de comandos.

Se invocan como modulos desde la carpeta `backend/`:

    python -m scripts.purge_demo_accounts

No forman parte de la aplicacion web: son tareas operativas que reutilizan sus
servicios. Por eso viven fuera del paquete `app`.
"""
