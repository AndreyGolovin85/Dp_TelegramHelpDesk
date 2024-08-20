from dotenv import load_dotenv
import os
import sys
import logging

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
ACCESS_KEY = os.getenv("ACCESS_KEY")

till_block_counter = {}

POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT"))
POSTGRES_DB = os.environ.get("POSTGRES_DB")

engine = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


def setup_logging(log_file, level=logging.INFO):
    """
    Настройка базового логгера.
    """

    logging.basicConfig(
        level=level,
        format="[%(asctime)s] - %(filename)s:%(lineno)d #%(levelname)-s - %(name)s - %(message)s",
        filename=log_file,
        filemode="w",
    )

    if not API_TOKEN or not ADMIN_ID or not ACCESS_KEY:
        logging.error("Отсутствуют переменные ENV.")
        sys.exit(1)
