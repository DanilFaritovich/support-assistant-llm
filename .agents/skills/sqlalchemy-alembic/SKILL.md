---
name: sqlalchemy-alembic
description: Persistence conventions for SQLAlchemy 2.x and Alembic, including ORM models, repositories, sessions, transactions, migrations, SQLite development/testing, and PostgreSQL production compatibility. Use when working with database persistence or schema changes.
---

# SQLAlchemy and Alembic Standard

Treat SQLAlchemy as an infrastructure/persistence implementation behind repository ports.

Treat Alembic as the authoritative migration mechanism for relational schema changes.

## Layer boundary

Keep concepts distinct:

- domain model: business representation;
- application port: persistence capability required by a use case;
- repository adapter: SQLAlchemy implementation;
- ORM model: database persistence representation;
- migration: schema evolution.

Do not let application services depend on SQLAlchemy ORM classes or sessions unless the project explicitly chooses a different architecture.

## SQLAlchemy style

Prefer SQLAlchemy 2.x APIs.

Use explicit statements such as:

```python
select(...)
update(...)
delete(...)
```

Follow the project's configured sync or async mode.

For async backends, use `AsyncSession` and async-capable drivers consistently.

Do not mix sync database I/O into async request handlers.

## ORM models

ORM models represent persistence, not the entire domain.

Keep database concerns here:

- table names;
- columns;
- indexes;
- relationships;
- database constraints;
- persistence-specific defaults.

Do not move complex business behavior into ORM models merely because the data is stored there.

## Repositories

Repository adapters implement application repository ports.

Responsibilities:

- execute queries;
- persist changes;
- map ORM models to internal objects when needed;
- encapsulate persistence-specific behavior.

Repositories should expose domain/application concepts instead of leaking raw SQLAlchemy internals outward.

## Session lifecycle

Use a clear session lifecycle.

For web applications, a request-scoped session is a common default.

Ensure sessions are:

- created predictably;
- rolled back after failed transactions when required;
- closed/released reliably.

Do not use one global mutable session shared by concurrent requests.

## Transaction ownership

Choose one clear transaction boundary.

Recommended default:

- application/use-case or unit-of-work boundary owns commit/rollback;
- repository methods query/add/update and may `flush` when generated values are needed;
- repositories do not silently commit unrelated operations.

Do not scatter `commit()` calls through many repository methods without an explicit architectural reason.

Use `flush()`, `commit()`, `refresh()`, and `rollback()` intentionally.

## Loading relationships

Select loading strategies intentionally.

Examples:

- `selectinload` for collections or when avoiding row multiplication is useful;
- `joinedload` when one joined query is appropriate.

Avoid accidental N+1 queries.

Do not eagerly load entire graphs by default.

## Constraints and indexes

Use database constraints for invariants that must remain true regardless of application code.

Examples:

- uniqueness;
- non-null requirements;
- foreign keys;
- check constraints where appropriate.

Create indexes based on query patterns rather than adding them blindly.

For performance changes, inspect actual queries and query plans when possible.

## PostgreSQL

PostgreSQL is the preferred production database when the project requires a production relational database.

Use a configurable database URL.

Do not hardcode database credentials.

Use PostgreSQL-specific features only when they provide clear value and are reflected in tests/migrations.

## SQLite

SQLite may be used for:

- lightweight local development;
- fast tests;
- simple prototypes;

when the application behavior is compatible.

Do not assume SQLite is equivalent to PostgreSQL.

Use PostgreSQL-backed integration tests when behavior depends on:

- PostgreSQL-specific types;
- locking;
- isolation;
- constraints;
- extensions;
- SQL syntax;
- concurrency semantics.

## Alembic

Use Alembic for every persistent relational schema change.

Typical workflow:

1. modify ORM/schema definitions;
2. create a migration;
3. inspect the generated migration;
4. correct it when autogeneration is incomplete or unsafe;
5. test upgrade;
6. test downgrade when the project requires reversible migrations.

Do not rely on `create_all()` as a production migration strategy.

## Migration quality

Migration files must be deterministic and reviewable.

Check:

- table/column names;
- foreign keys;
- indexes;
- constraints;
- data migrations;
- defaults;
- downgrade behavior.

For destructive changes, consider compatibility and data preservation explicitly.

## Application startup

Do not run uncontrolled schema creation on every production application startup.

If migrations are automated in deployment, use a dedicated migration step before application startup.

Example:

```text
deploy
 -> run Alembic migrations
 -> start backend
 -> health check
```

## Testing

Unit tests should mock/fake repository ports rather than SQLAlchemy.

Repository behavior belongs in integration tests.

Migration tests should be added when schema complexity or deployment risk justifies them.

When PostgreSQL-specific behavior matters, run the relevant integration coverage against PostgreSQL rather than only SQLite.
