from chat_app.config import load_config
from chat_app.postgres.service import ensure_postgres_ready


def main() -> int:
    ensure_postgres_ready(load_config())
    print("PostgreSQL 初始化完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
