from google.auth.transport.requests import Request
from dotenv import load_dotenv
from utils import (
    get_env,
    load_env_variables_from_spreadsheet,
    change_spreadsheet_env_variable,
    Email,
)
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def main():
    load_dotenv()  # take environment variables from .env.
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    load_env_variables_from_spreadsheet()

    EMAIL_OAUTH_CREDENTIALS = get_env("EMAIL_OAUTH_CREDENTIALS")
    EMAIL_OAUTH_TOKEN = get_env("EMAIL_OAUTH_TOKEN")

    email_oauth_credentials = Email.decode_oauth_credentials(EMAIL_OAUTH_CREDENTIALS)
    email_oauth_token = Email.decode_oauth_credentials(EMAIL_OAUTH_TOKEN)

    creds = Credentials.from_authorized_user_info(email_oauth_token, SCOPES)
    if not creds or not creds.valid:
        print("creds_were_invalid")
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                client_config=email_oauth_credentials, scopes=SCOPES
            )
            creds = flow.run_local_server(port=0)
        change_spreadsheet_env_variable(
            "EMAIL_OAUTH_TOKEN",
            Email.encode_oauth_credentials(json.loads(creds.to_json())),
        )


main()
