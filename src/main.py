import os

from dotenv import load_dotenv

load_dotenv()


def main():
    print("Hello from caption-mate!")
    print(os.getenv("OAI_MODEL_O4_MINI"))
    print(os.getenv("OAI_API_KEY"))
    print(os.getenv("OAI_BASE_URL"))


if __name__ == "__main__":
    main()
