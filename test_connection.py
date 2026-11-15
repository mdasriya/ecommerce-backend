from sqlalchemy import text

from app.database.connection import engine


try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

        print("Neon Database Connected!")

        print(result.fetchone())

except Exception as error:
    print("Database Connection Failed!")
    print(error)