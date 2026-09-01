"""Verify DATABASE_URL and create/upgrade the VacancyScore tables."""

from app import store


def main() -> None:
    store.init_db()
    status = store.database_status()
    print(
        "Database ready: "
        f"{status['dialect']}://{status['host']}/{status['database']}"
    )


if __name__ == "__main__":
    main()
