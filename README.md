# Order Takeout Manager Prototype

This repository creates a prototype of a order pickup manager that was submitted for the Dev/Twilio Hackathon.  The prototype application uses Twilio APIs to create a web application for small businesses to communicate with their customers to make order pickup a more efficient process.

## Prerequisites for this Project

Before getting started there are a couple things you need to have setup.

- If you don't have a Twilio account already, you can use this [referral link](www.twilio.com/referral/J5x4pK) to setup your account with a free $10 to fund your account to get started.
- Install [ngrok](https://ngrok.com/) to connect our Autopilot webhooks to.
- Setup the [Twilio CLI tool](https://www.twilio.com/docs/twilio-cli/quickstart) and install the [Autopilot CLI plug-in](https://www.twilio.com/docs/autopilot/twilio-autopilot-cli) which will be used to deploy our Autopilt bot.
- A Twilio phone number.  You can log into the Twilio console and [get one here](https://www.twilio.com/console/phone-numbers/search).

## Install Project Dependencies

Start by cloning this repository and installing all the package dependencies in `requirements.txt`.

```
Flask==1.1.1
twilio==6.35.2
python-dotenv==0.12.0
```

## Setup ngrok

Ngrok is used to allow Twilio to communicate with your local Flask application.  If you haven't already, [download and install ngrok](https://ngrok.com).  Once ngrok is installed you can begin using ngrok by typing `./ngrok http 5000` in the commandline.  Ngrok creates a unique URL that will forward any requests made to that URL to your local development environment.

There should be two URLs labeled "Forwarding".  The "https://" forwarding URL will be used as the webhooks to process data collected from your Autopilot bot in the next step.

## Setting Up the Autopilot Bot

When customers arrive to pickup their orders we want to gather some basic information about them.  We want to know the customer name to match to the name on the order and we want to know if the customer is waiting in their car or not (if it's a bad weather day this could be the case).  If the customer is waiting in their car we want to collect some more information about the car so you can get the order out to them.  Collecting this information will be done using an Autopilot bot.

The schema for the Autopilot bot is available in the GitHub repo in the `schema.json` file.  The schema defines all the different tasks for the bot.  There are separate tasks for getting the basic customer information, car details, as well as to handle when people say a friendly "hello".  For the `confirm_arrive` and `get_car_details` tasks the Flask application needs to process the information provided by the user.  To send the input provided by the user to your application you need to edit `schema.json` to point the webhooks to your ngrok domain.

In the schema file find the `confirm_arrive` task.  Substitute your ngrok URL from the previous step into the `redirect` value:

```json
      "uniqueName" : "confirm_arrive",
      "actions" : {
        "actions" : [
          {
            "say" : "Thank you for choosing our business!  Tell us about your order and we'll get it out to you!"
          },
          {
            "collect" : {
              "on_complete" : {
                "redirect" : "<YOUR NGROK URL>/bot/confirm-in-car"
              },
              "name" : "customer_name",
              "questions" : [
                {
                  "question" : "What is the name on the order?",
                  "name" : "first_name"
                },
                {
                  "type": "Twilio.YES_NO",
                  "question": "Are you waiting in your car?",
                  "name": "in_car"
                }
              ]
            }
          }
        ]
      },
```

If users are waiting in their car then some follow-up questions are asked to get some details about the car they are in.  The `redirect` value here needs to updated for your ngrok URL:

```json
      "uniqueName": "get_car_details",
      "actions": {
        "actions": [
          {
            "collect": {
              "name": "car_detail",
              "questions": [
                {
                  "question": "What is the color and make of the car?",
                  "name": "car_make"
                },
                {
                  "question": "What is your license plate number?",
                  "name": "car_license"
                }
              ],
              "on_complete": {
                "redirect": "<YOUR NGROK URL>/bot/parse-car-details"
              }
            }
          }
        ]
      }
```

Now the webhooks for your Autopilot bot are configured to use the Flask endpoints in your local environment.

### Deploying the Autopilot Bot

Now that the Autopilot bot has been configured to use your Flask endpoints you're ready to deploy the bot for use.  The Twilio CLI is the quickest way to deploy and manage your Autopilot bots.  If you haven't already setup the [Twilio CLI](https://www.twilio.com/docs/twilio-cli/quickstart) and installed the [Twilio Autopilot CLI plug-in](https://www.twilio.com/docs/autopilot/twilio-autopilot-cli).

Once you have the Twilio CLI and Autopilot plug-in ready open a terminal window and navigate to the directory containing your `schema.json` file.  Once there you can deploy your bot by typing:

```commandline
twilio autopilot:create --schema schema.json
```

Your Autopilot bot is deployed!

If you make updates to your bot all you have to do is make those changes in `schema.json` and then use the `update` command in the CLI:

```commandline
twilio autopilot:update --schema schema.json
```

### Attaching Autopilot to Your Twilio Number

The last step is to attach the Autopilot bot to your Twilio number so that when customers text your number Autopilot will handle their request.

Log into the Twilio console and select **Autopilot** from the menu on the left.  Click on the **order_pickup** bot you just created.

Select **Channels** from the menu on the left and then choose **Programmable Messaging**.

Copy the **MESSAGING URL**.

Select **Phone Numbers** from the left menu of products and services.  Choose the phone number you want to use from the list.

Scroll down to the bottom and paste the Messaging URL into the **A Message Comes In** text box.

Now you have an interactive Autopilot bot ready to get your order arrival details from you!

## Creating a Sync Map

With your Autopilot setup the next step is to initialize a Sync Map where orders will be stored.  [Sync](https://www.twilio.com/sync) allows the platform to track real-time updates for customer arrivals and display new information through the platform without having to refresh the page.

Before using Sync, you have to create a Sync service to use, which similar to Autopilot can be done through the commandline in a couple commands.

First, create a Sync service by typing the following into the commandline:

```commandline
twilio api:sync:v1:services:create
```

In the response find and copy the `sid` attribute.  Next, you need to create a map and associate that with the service.

In the commandline type the following where you will substitute the `sid` from above.

```commandline
twilio api:sync:v1:services:maps:create --service-sid <YOUR_SYNC_SERVICE_SID>
```

In the response there will be a `sid` beginning with "MP".  Keep this handy as it will be needed in setting up the Flask application.

Your Sync Map is ready for use!

## Generate a Twilio API Key

The last piece of setup is you need to [generate an API key](https://www.twilio.com/console/project/api-keys) that will be used to handle JavaScript requests.  After you create the key keep track of the API Key and Secret that are provided.  You'll need those in the next step.
 

## Setting Up the Flask Environment

Flask will serve as the back-end of the platform providing the web pages as well as the webhook for the Autopilot responses from the customers.  The `app.py` file contains the core code for the application that handles interactions with the web application and the appropriate API calls with Twilio.  To setup the Flask application you need to fill in the details of the `.env` file with details from your Twilio account.  These environment variables are used to make your API calls with Twilio.  Do not share them with anyone!

- `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` come directly from the Twilio console with you login
- Fill in `TWILIO_API_KEY` and `TWILIO_API_SECRET` with the info generated in the previous step
- `TWILIO_SYNC_SERVICE_SID` and `TWILIO_SYNC_MAP_SID` come from creating the Sync Map with the CLI
- `TWILIO_FROM_NUMBER` is the phone number you purchased.  Make sure it's in E.164 format with (ex. +14155552671)

```
# Required for all uses
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_API_KEY=
TWILIO_API_SECRET=

# Twilio Sync SIDs
TWILIO_SYNC_SERVICE_SID=
TWILIO_SYNC_MAP_SID=

# Twilio Number to send messages from.
TWILIO_FROM_NUMBER=
```

Once you have all the environmental variables filled out you can deploy the Flask application.  From the commandline make sure you are in the directory of the application and then enter:

```commandline
python app.py
```

Your application is now live!