from datetime import datetime
from dataclasses import dataclass
from utils import (
    get_env,
    get_month,
    create_summary,
    Venmo,
    Email,
)
from dotenv import load_dotenv


@dataclass
class LatePayment:
    id: str
    name: str
    username: str
    description: str
    amount: float
    status: str = "ACTIVE"


def main(now):
    load_dotenv()

    month = get_month(now)

    ACCESS_TOKEN = get_env("VENMO_ACCESS_TOKEN")
    venmo = Venmo(ACCESS_TOKEN)
    email = Email()

    all_requests = venmo.get_all_requests()
    late_payments = []
    success_payments = []
    fail_payments = []

    for request in all_requests:
        if (
            "Tribe tuition for the month of" in request.note
            and "Late payment for:" not in request.note
        ):
            late_payments.append(
                LatePayment(
                    id=request.target.id,
                    name=request.target.display_name,
                    username=request.target.username,
                    amount=10.0,
                    description="Late payment for: {}".format(request.note),
                )
            )

    for payment in late_payments:
        success = venmo.request_money(payment.id, payment.amount, payment.description)
        if success:
            success_payments.append(payment)
        else:
            fail_payments.append(payment)

    email.send_email(
        "{} Venmo summary for LATE Tribe tuition".format(month),
        create_summary(success_payments, fail_payments),
    )

    if len(late_payments) == len(success_payments):
        print(
            "✅ Ran script successfully and sent "
            + str(len(success_payments))
            + " Venmo requests."
        )
    else:
        print(
            "❌ Something went wrong. Only sent "
            + str(len(success_payments))
            + "/"
            + str(late_payments)
            + " venmo requests."
        )


now = datetime.now()
main(now)
