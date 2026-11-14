from alembic import context

import app.main  # noqa: F401  (imports every module, so all tables are on Base.metadata)
from app.core.db import Base, engine

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
