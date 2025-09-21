from dotenv import load_dotenv
import os

# Load .env file
load_dotenv(verbose=True)

# Get Postgres destination values
DEST_HOST = os.getenv("DEST_HOST")
DEST_PORT = os.getenv("DEST_PORT")
DEST_DB   = os.getenv("DEST_DB")
DEST_USER = os.getenv("DEST_USER")
DEST_PASS = os.getenv("DEST_PASS")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

REQUIRED_FIELDS = os.getenv("REQUIRED_FIELDS")