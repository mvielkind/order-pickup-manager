import os
import json
import string
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import (
    SyncGrant
)


app = Flask(__name__)
load_dotenv(".env")


TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SYNC_SERVICE_SID = os.getenv("TWILIO_SYNC_SERVICE_SID")
TWILIO_SYNC_MAP_SID = os.getenv("TWILIO_SYNC_MAP_SID")

# Establish the Twilio Client
TWILIO_CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@app.route("/")
def main():
    return render_template("index.html")


@app.route("/new-order")
def new_order():
    """
    Renders the page for businesses to enter data for new orders.
    """
    return render_template("new_order.html")


@app.route("/bot/confirm-in-car", methods=["POST"])
def confirm_in_car():
    """
    Endpoint for the confirm_arrive Autopilot task.

    Parses customer responses.  If member indicates they are waiting in their vehicle they will be handed off to
    another Autopilot task to get more details.  Otherwise, the business is alerted the customer has arrived and
    the customer interaction is complete.
    """
    memory = json.loads(request.values.get("Memory"))
    in_car = memory["twilio"]["collected_data"]["customer_name"]["answers"]["in_car"]["answer"]

    # If customer is waiting in the car get more details.
    if in_car == "Yes":
        return {"actions": [
            {
                "redirect": "task://get_car_details"
            }

        ]}

    # Otherwise alert the business the customer has arrived for their order.
    response = alert_arrival(memory)

    return response


@app.route("/bot/parse-car-details", methods=["POST"])
def parse_car_details():
    """
    Endpoint for the get_car_details Autopilot task.

    Gets the customer responses to the task and passes those to the business to update the order with the additional
    detail.  Customer is thanked for their order.
    """
    memory = json.loads(request.values.get("Memory"))

    response = alert_arrival(memory)

    return response


def alert_arrival(customer_input):
    """
    Updates order details with the input collected by the customer from the Autopilot bot.
    :param customer_input: Memory object from the Autopilot bot with customer response.
    """
    # Parse incoming data.
    collected = customer_input["twilio"]["collected_data"]
    arrival_details = dict()
    arrival_details["in_car"] = collected["customer_name"]["answers"]["in_car"]["answer"]

    phone_num = customer_input["twilio"]["sms"]["From"]

    if "car_detail" in collected:
        arrival_details["car_make"] = collected["car_detail"]["answers"]["car_make"]["answer"]
        arrival_details["car_license"] = collected["car_detail"]["answers"]["car_license"]["answer"]

    arrival_details["status"] = "Arrived"

    # Get order information.
    order = TWILIO_CLIENT.sync.services(TWILIO_SYNC_SERVICE_SID).\
        sync_maps(TWILIO_SYNC_MAP_SID).\
        sync_map_items(phone_num).\
        fetch().\
        data

    # Add new details to the order.
    for k, v in arrival_details.items():
        order[k] = v

    # Update the order details.
    updated_order = TWILIO_CLIENT.sync.services(TWILIO_SYNC_SERVICE_SID).\
        sync_maps(TWILIO_SYNC_MAP_SID).\
        sync_map_items(phone_num).\
        update(
        data=order
    )

    # Response to provide back to the customer.
    return {"actions": [
        {"say": "Thank you!  We'll bring your order right away!"}
    ]}


@app.route("/send-text", methods=["POST"])
def send_text():
    """
    Creates a customized text message confirming the order and alerting the customer about the pickup service.
    """
    customer_name = request.form["customer-name"]
    to_num = request.form["to-number"]

    # Replace punctuation and spaces in phone number.
    e164_num = to_num.translate(str.maketrans('', '', string.punctuation)).replace(" ", "")
    e164_num = f"+1{e164_num}"

    # Send text message to the customer.
    TWILIO_CLIENT.messages.create(
        to=e164_num,
        from_=os.getenv("TWILIO_FROM_NUMBER"),
        body=f"Thanks for your order {customer_name}!\n\nTo make order pickup easier send ARRIVE to this number to let us know you're here."
    )

    # Create new Sync Map entry for the order.
    try:
        sync_map_item = TWILIO_CLIENT.sync \
            .services(TWILIO_SYNC_SERVICE_SID) \
            .sync_maps(TWILIO_SYNC_MAP_SID) \
            .sync_map_items \
            .create(key=e164_num, data={
                'name': customer_name,
                'status': 'Order Placed',
                'readPhone': to_num
            })
    except TwilioRestException as ex:
        print(ex.msg)

    return render_template("order_created.html", customer_name=customer_name, phone_number=to_num)


@app.route("/send-order-reminder", methods=["POST"])
def send_order_reminder():
    """
    Sends a reminder to the customer when their order is ready.
    """
    to_num = request.form["orderID"]

    # Get name on order.
    order_item = TWILIO_CLIENT.sync.\
        services(TWILIO_SYNC_SERVICE_SID).\
        sync_maps(TWILIO_SYNC_MAP_SID).\
        sync_map_items(to_num).\
        fetch()

    customer_name = order_item.data["name"]

    msg = f"Hi {customer_name}!  Your order is ready for pickup!\n\n" \
        f"When you are here to pickup your order text ARRIVE and we'll bring it out to you!"

    response = TWILIO_CLIENT.messages.create(
        to=to_num,
        from_=os.getenv("TWILIO_FROM_NUMBER"),
        body=msg
    )

    # Update the order status.
    order_item.data["status"] = "Reminder Sent"
    order_item.update(data=order_item.data)

    return "SUCCESS"


@app.route('/orders')
def orders():
    """
    Gets active order objects from the Sync Map and populates the webpage.
    """
    all_orders = TWILIO_CLIENT.sync.\
                       services(TWILIO_SYNC_SERVICE_SID).\
                       sync_maps(TWILIO_SYNC_MAP_SID).\
                       sync_map_items.\
                       list()

    return render_template("order_list.html", orders=all_orders)


@app.route("/sync-token", methods=["GET"])
def token():
    """
    Generate the access token to access Sync Map.
    """
    account_sid = TWILIO_ACCOUNT_SID
    api_key = os.getenv("TWILIO_API_KEY")
    api_secret = os.getenv("TWILIO_API_SECRET")

    # Create access token with credentials
    token = AccessToken(account_sid, api_key, api_secret, identity="sync")

    sync_grant = SyncGrant(service_sid=TWILIO_SYNC_SERVICE_SID)
    token.add_grant(sync_grant)

    return jsonify(identity="sync", token=token.to_jwt().decode('utf-8'), syncListID=TWILIO_SYNC_MAP_SID)


if __name__ == "__main__":
    app.run()
