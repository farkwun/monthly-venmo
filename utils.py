import os
from venmo_api import Client, PaymentStatus
from notifiers import get_notifier
from google.auth.transport.requests import Request
import gspread
import json
import base64
from dataclasses import dataclass
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from requests import HTTPError


@dataclass
class RequestUser:
    username: str
    id: str
    tuition: float
    status: str
    name: str


def get_env(env):
    """
    Verfies that an environment variable exists
    and returns it.

    Exits script if not found.
    """
    if os.getenv(env):
        print(f"✅ {env} is available in the environment.")
        return os.getenv(env)
    else:
        print(f"❌ Can't find {env} in environment.")
        print("   Exiting script. Please add and run again.")
        quit()


def load_env_variables_from_spreadsheet():
    SERVICE_ACCOUNT_CREDENTIALS = get_env("SERVICE_ACCOUNT_CREDENTIALS")
    CREDENTIALS_SPREADSHEET_KEY = get_env("CREDENTIALS_SPREADSHEET_KEY")
    google = GoogleDrive(
        GoogleDrive.decode_service_credentials(SERVICE_ACCOUNT_CREDENTIALS)
    )
    sheet = google.client.open_by_key(CREDENTIALS_SPREADSHEET_KEY)
    worksheet = sheet.get_worksheet(0)
    records = worksheet.get_all_records()
    for record in records:
        os.environ[record["API"]] = record["token"]


def change_spreadsheet_env_variable(variable_name, variable_value):
    SERVICE_ACCOUNT_CREDENTIALS = get_env("SERVICE_ACCOUNT_CREDENTIALS")
    CREDENTIALS_SPREADSHEET_KEY = get_env("CREDENTIALS_SPREADSHEET_KEY")
    google = GoogleDrive(
        GoogleDrive.decode_service_credentials(SERVICE_ACCOUNT_CREDENTIALS)
    )
    values = google.get_all_values_from_spreadsheet(CREDENTIALS_SPREADSHEET_KEY)
    for value in values:
        if value[0] == variable_name:
            value[1] = variable_value
    google.overwrite_values(CREDENTIALS_SPREADSHEET_KEY, values)


env_vars = ["VENMO_ACCESS_TOKEN", "SERVICE_ACCOUNT_CREDENTIALS", "SPREADSHEET_KEY"]


def create_summary(successfulRequests, unsuccessfulRequests):
    return """Failed to send Venmo requests to:

{failedRequests}

Successfully sent Venmo requests to:

{successfulRequests}
    """.format(
        failedRequests="\n".join(
            [
                f"- {friend.name} - @{friend.username} (status: {friend.status})"
                for friend in unsuccessfulRequests
            ]
        ),
        successfulRequests="\n".join(
            [
                f"- {friend.name} - @{friend.username} (status: {friend.status})"
                for friend in successfulRequests
            ]
        ),
    )


def verify_env_vars(vars, numOfExpected):
    """
    Verifies the list of vars are defined in the environment.
    """

    availableEnvVars = []

    for var in vars:
        # If it returns the env, which would be True
        # then we know it's available
        if get_env(var):
            availableEnvVars.append(var)

    if len(availableEnvVars) == numOfExpected:
        return True
    else:
        # This will technically never run
        # because if one doesn't exist, then get_env quits
        # but adding here for posterity
        return False


def get_env_vars(vars):
    """
    Returns an array of the vars after getting them
    """

    allVars = []
    for var in vars:
        allVars.append(os.getenv(var))

    return allVars


def get_month(now):
    """
    Returns the current month.
    Example: April
    """

    month = now.strftime("%B")
    return month


class Venmo:
    def __init__(self, access_token):
        self.client = Client(access_token=access_token)

    def get_user_id_by_username(self, username):
        user = self.client.user.get_user_by_username(username=username)
        if user:
            return user.id
        else:
            print("ERROR: user did not comeback. Check username.")
            return None

    def request_money(self, id, amount, description):
        # Returns a boolean: true if successfully requested
        return self.client.payment.request_money(amount, description, id)

    def get_all_requests(self, status=PaymentStatus.PENDING):
        return [
            payment
            for payment in self.client.payment.get_charge_payments()
            if payment.status == status
        ]


class Telegram:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = get_notifier("telegram")

    def send_message(self, message):
        self.client.notify(message=message, token=self.bot_token, chat_id=self.chat_id)


class GoogleDrive:
    def __init__(self, service_credentials):
        self.client = gspread.service_account_from_dict(service_credentials)

    def get_all_values_from_spreadsheet(self, spreadsheet_key, worksheet_index=0):
        sheet = self.client.open_by_key(spreadsheet_key)
        worksheet = sheet.get_worksheet(worksheet_index)
        values = worksheet.get_all_values()
        return values

    def overwrite_values(self, spreadsheet_key, values, worksheet_index=0):
        sheet = self.client.open_by_key(spreadsheet_key)
        worksheet = sheet.get_worksheet(worksheet_index)
        worksheet.update(values)

    def get_all_records_from_spreadsheet(self, spreadsheet_key, worksheet_index=0):
        VENMO_ACCESS_TOKEN = get_env("VENMO_ACCESS_TOKEN")
        venmo = Venmo(VENMO_ACCESS_TOKEN)

        # see sample.csv for an example of how this should look
        sheet = self.client.open_by_key(spreadsheet_key)
        worksheet = sheet.get_worksheet(worksheet_index)
        records = worksheet.get_all_records()

        return [
            RequestUser(
                **record, **{"id": venmo.get_user_id_by_username(record["username"])}
            )
            for record in records
        ]

    @classmethod
    def decode_service_credentials(cls, base64_encoded_credentials):
        encoded_key = str(base64_encoded_credentials)[2:-1]
        return json.loads(base64.b64decode(encoded_key).decode("utf-8"))

    @classmethod
    def encode_service_credentials(cls, json_credentials):
        import json
        import base64

        # convert json to a string
        service_key = json.dumps(json_credentials)

        # encode service key
        encoded_service_key = base64.b64encode(service_key.encode("utf-8"))
        return encoded_service_key


class Email:
    def __init__(self):
        self.SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

        load_env_variables_from_spreadsheet()

        RECIPIENT_EMAIL = get_env("RECIPIENT_EMAIL")
        EMAIL_OAUTH_CREDENTIALS = get_env("EMAIL_OAUTH_CREDENTIALS")
        EMAIL_OAUTH_TOKEN = get_env("EMAIL_OAUTH_TOKEN")

        self.email_oauth_credentials = Email.decode_oauth_credentials(
            EMAIL_OAUTH_CREDENTIALS
        )
        self.email_oauth_token = Email.decode_oauth_credentials(EMAIL_OAUTH_TOKEN)

        creds = Credentials.from_authorized_user_info(
            self.email_oauth_token, self.SCOPES
        )
        if not creds or not creds.valid:
            print("creds_were_invalid")
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    client_config=self.email_oauth_credentials, scopes=self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            change_spreadsheet_env_variable(
                "EMAIL_OAUTH_TOKEN",
                Email.encode_oauth_credentials(json.loads(creds.to_json())),
            )
        self.recipient_email = RECIPIENT_EMAIL

    def get_encoded_email_token(self):
        flow = InstalledAppFlow.from_client_config(
            client_config=self.email_oauth_credentials, scopes=self.SCOPES
        )
        creds = flow.run_local_server(port=0)
        return Email.encode_oauth_credentials(creds)

    def send_email(self, subject, text):
        RECIPIENT_EMAIL = get_env("RECIPIENT_EMAIL")
        creds = Credentials.from_authorized_user_info(
            self.email_oauth_token, self.SCOPES
        )

        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(text)
        message["to"] = RECIPIENT_EMAIL
        message["subject"] = subject
        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}

        try:
            message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            print(f'sent message to {message} Message Id: {message["id"]}')
        except HTTPError as error:
            print(f"An error occurred: {error}")
            message = None

    @classmethod
    def decode_oauth_credentials(cls, base64_encoded_credentials):
        encoded_key = str(base64_encoded_credentials)[2:-1]
        return json.loads(base64.b64decode(encoded_key).decode("utf-8"))

    @classmethod
    def encode_oauth_credentials(cls, json_credentials):
        import json
        import base64

        # convert json to a string
        service_key = json.dumps(json_credentials)

        # encode service key
        encoded_service_key = base64.b64encode(service_key.encode("utf-8"))
        return str(encoded_service_key)
