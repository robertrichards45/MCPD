# Production Database Persistence

Officer accounts, passwords, assignments, saved drafts, forms, and report records must live in a persistent database.

## Railway Requirement

Use Railway Postgres for production:

```text
DATABASE_URL=<Railway Postgres connection string>
APP_ENV=prod
REQUIRE_PERSISTENT_DATABASE=1
```

Do not use the default local SQLite path on Railway:

```text
DATABASE_URL=sqlite:///data/app.db
```

Railway rebuilds can replace the app filesystem. If the app uses SQLite inside the app folder, officer accounts may disappear after a deploy and officers will have to recreate accounts.

## SQLite With A Railway Volume

SQLite is only acceptable in production if it is stored on a mounted persistent Railway volume:

```text
DATABASE_URL=sqlite:////data/app.db
RAILWAY_VOLUME_MOUNT_PATH=/data
REQUIRE_PERSISTENT_DATABASE=1
```

## Safety Guard

The app now refuses to boot on Railway if `DATABASE_URL` points to unsafe local SQLite storage. This is intentional. It is better for deploy to fail clearly than to start with an empty database and make officers recreate accounts.

