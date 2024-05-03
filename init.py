from venmo_api import Client
from dotenv import load_dotenv
from notifiers import get_notifier
from datetime import datetime

from utils import (
    create_summary,
    get_env,
    env_vars,
    get_month,
    Venmo,
    Email,
    GoogleDrive,
)


def main(now):
    """
    The main function which initiates the script.
    """

    load_dotenv()  # take environment variables from .env.
    actualVars = []
    for var in env_vars:
        actualVars.append(get_env(var))

    (access_token, service_account_credentials, spreadsheet_key) = actualVars

    month = get_month(now)
    venmo = Venmo(access_token)
    google = GoogleDrive(
        GoogleDrive.decode_service_credentials(service_account_credentials)
    )
    email = Email()

    friends = google.get_all_records_from_spreadsheet(spreadsheet_key)

    successfulRequests = []
    unsuccessfulRequests = []
    expectedRequests = len(friends)

    for friend in friends:
        if friend.status != "ACTIVE" or friend.id is None:
            unsuccessfulRequests.append(friend)
            continue
        id = friend.id
        description = "Tribe tuition for the month of " + month + "— Sent by 👹"
        amount = friend.tuition

        success = venmo.request_money(id, amount, description)
        if success:
            successfulRequests.append(friend)
        else:
            unsuccessfulRequests.append(friend)

    email.send_email(
        "{} Venmo summary for Tribe tuition".format(month),
        create_summary(successfulRequests, unsuccessfulRequests),
    )

    if len(successfulRequests) == expectedRequests:
        print(
            "✅ Ran script successfully and sent "
            + str(expectedRequests)
            + " Venmo requests."
        )
    else:
        print(
            "❌ Something went wrong. Only sent "
            + str(len(successfulRequests))
            + "/"
            + str(expectedRequests)
            + " venmo requests."
        )


now = datetime.now()
main(now)
