import os
from venmo_api import Client, PaymentPrivacy
from notifiers import get_notifier
import gspread
import json
import base64
from dataclasses import dataclass


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


env_vars = ["VENMO_ACCESS_TOKEN", "SERVICE_ACCOUNT_CREDENTIALS", "SPREADSHEET_KEY"]


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
