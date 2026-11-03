"""
Create the tables and seed the scopes for local development. On the deployed environments the admin schema in the
NVI database is managed by the NVI migrations, so this only runs from docker/init.sh.
"""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_config
from app.db.db import Database
from app.db.models.scope import ScopeEntity
from app.models.scopes import AuthorizationScope

if __name__ == "__main__":
    db = Database(get_config().database)
    if db.engine.dialect.name == "postgresql":
        with db.engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS admin"))
    db.generate_tables()

    with Session(db.engine) as session:
        existing = set(session.scalars(select(ScopeEntity.name)))
        session.add_all(ScopeEntity(name=scope) for scope in AuthorizationScope if scope not in existing)
        session.commit()
