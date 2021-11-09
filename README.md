# RTA-TIME SMS app

Creates a virtual phone number that accepts 5-digit GCRTA stop numbers and replies with the next three arriving vehicles for each route serving that transit stop. Uses [Twilio](https://www.twilio.com/), Amazon Web Services (AWS) [Lambda](https://aws.amazon.com/lambda/), and Python 3.8 with modules such as Flask (for serving the app) and Zappa (for simple AWS serverless deployment). Optional use of an AWS [Relational Data Server (RDS)](https://aws.amazon.com/rds/) running PostgreSQL for tracking of app usage. Assumes that you already have setup your AWS [credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html) in command-line.

If a rider sends a 5-digit Stop # (often displayed on the signs) by SMS text message, e.g.,
```
03457
```
then the following text message is returned to the sender
```
DETROIT AV & W 65TH ST
26: 1131a, 1147a
26A: 1117a
```


## Description & Purpose

This app incorporates the code found in my [rtatime-api](https://github.com/trivisonno/rtatime-api) repo. See that project README for more specific information on how the data is pulled from GCRTA's NextConnect vehicle tracking system.

GCRTA does not presently have much in-field technology installed to help riders track the real-time arrivals of transit vehicles. (Many rail stops display vehicle arrival times, and a few of the busiest bus stops have arrival info technology, such as around Public Square and on the HealthLine). These physical devices also likely have maintenance and connectivity challenges, which present issues for further deployment, especially at stops with lower boarding numbers.

Some smartphone applications are able to provide real-time vehicle location information, such as the Transit app. GCRTA also provides a [website](http://nextconnect.riderta.com/LiveDepartureTimes) that allows users to select a route, a direction, and then a stop to find the next arrival times. However, riders without smartphones or without data plans cannot access these web-based resources.

This SMS app provides a missing piece of rider technology, particular to those riders affected by digital divide challenges. Most riders without smartphones or data plans are able to send and receive SMS text messages, and are familiar with how to send text messages.

Twilio is one of the larger virtual telephony platforms, and is a common tool in these types of applications. Each SMS message costs about $0.0075. So for a rider to send one message with the 5-digit stop number and to receive one message with the arrival information costs $0.015 total. Full SMS pricing for Twilio is [here](https://www.twilio.com/sms/pricing/us).

One challenge is attempting to estimate likely total project costs if this system is deployed system-wide, since ridership numbers and technology needs are not very well-understood outside of GCRTA. Preliminary sample data with a small group of riders indicate use of the system a few times each week, although this may be different among different rider groups. A ballpark guess is between $150-250K annually (~0.1% of GCRTA's annual budget). SMS messaging costs may be lowered with a few optimization strategies, but this is not a present focus of this project.


## Getting Started

Ensure that you have Python 3+ installed on your system. I recommend using pipenv for testing. You should also have your AWS credentials configured and a Twilio virtual phone number selected.


### Dependencies & Assumptions

* Python 3.8, Flask, Zappa, Twilio
* If using the database feature, the [pgAdmin4](https://www.pgadmin.org/) application may be helpful, but is optional.
* Assumes knowledge of command-line and AWS account is already configured.


### Installing

* Download the repo to your computer
* Create a pipenv for your pip packages such as flask and/or zappa
* Accept all of the Zappa defaults when you run **zappa init**
```
git clone https://www.github.com/trivisonno/rtatime-sms
cd rtatime-sms
pipenv shell --python 3.8
pip install flask zappa twilio
zappa init
```

If using the optional database, also install psycopg2 and timezone/pytz modules:
```
pip install aws-psycopg2 psycopg2-binary pytz
```


### Connecting to Twilio
After installing the required Python packages, the app and your Twilio account must be connected together. First, create a Twilio account ([instructions](https://www.youtube.com/watch?v=vMG3iIqflR8&t=180s)). Next, select a phone number to use with the app ([instructions](https://www.youtube.com/watch?v=vMG3iIqflR8&t=394s)). Third, find your Account SID and Auth Token on your Twilio Console ([instructions](https://www.youtube.com/watch?v=Kcnplo9Z_F4)). The Account SID and Auth Token are two important variables that we need for the next step below. (It's worth noting here that if you use only a free trial account on Twilio, all of your SMS messages will have extra text added to them, and you will be sandboxed and able to text only numbers that you can personally verify as your own. Upgrade to a normal paid account to unlock all of the texting features.)

The app uses environment variables that are set in a **zappa_settings.json** file that is created after the zappa init command above. Open that file in your text editor and add the following variables with the appropriate information similar to the included **zappa_settings.sample.json** file:
```
    "include": [
            "routesAtEachStop.json", "test-postedStopIDMapping.json", "test-rta_stops.geojson"
        ],
        "environment_variables": {
            "twilio_account_sid": "<YOUR_TWILIO_ACCOUNT_SID_HERE>",
            "twilio_auth_token": "<YOUR_TWILIO_AUTH_TOKEN_HERE>",
            "psycopg2_user": "",
            "psycopg2_password": "",
            "psycopg2_host": "",
            "psycopg2_dbname": "",
            "psycopg2_port": "",
            "debug_phone_number": ""
        }
```

Once the Account SID and Auth Token is added to the zappa_settings.json file, we can begin testing the app locally with Flask and/or deploy to AWS with Zappa.

Testing locally doesn't actually send any SMS messages, but you can test how the messages would look, just by using your web browser. To test locally with Flask, run from the command-line:
```
export FLASK_APP=app.py
flask run
```
This starts a local web server on your computer, usually on port 5000. If it uses some other port, make sure to use that port number in the URL below.

Try a 5-digit stop number (Stop # 03457 as example) in the Body parameter and include a 10-digit phone number in the From parameter, using your web browser:
```
http://127.0.0.1:5000/sms?Body=03457&From=+15555555555
```

In your web browser, you should see text like this:
```
DETROIT AV & W 65TH ST 26: 503p, 531p 26A: 522p
```

Don't worry, the SMS messages are properly formatted with line breaks when sent.

Once you confirm that the app is retrieving correct real-time arrival data from GCRTA's systems, we can deploy to AWS using Zappa.

Deploy with zappa:
```
zappa deploy dev
```

Zappa will automatically create an API Gateway URL for you, and you'll see something like this below in your Terminal command-line:
```
Your updated Zappa deployment is live!: https://abc1234.execute-api.us-east-1.amazonaws.com/dev
```

Once deployed to AWS, you can also test the app from your web browser:
```
https://abc1234.execute-api.us-east-1.amazonaws.com/dev/sms?Body=03457&From=+15555555555
```

Now, we will go to the Twilio Console and use our API Gateway URL as a Webhook with the Twilio messaging system. [Here's](https://youtu.be/SHt21VwFj-A?t=21) a video explaining where to go to update your Webhook URL. In the Messaging section, add your URL to the "When A Message Comes In" field, and leave "Webhook" and "HTTP POST" selected. Also add '/sms' to the end, so the URL looks like this:
```
https://abc1234.execute-api.us-east-1.amazonaws.com/dev/sms
```

Now, SMS message data will be forwarded to your app for a reply with the arrival info.

If you choose to use the database features to track app usage, then there is also a Dashboard panel provided that can be accessed at:
```
http://127.0.0.1:5000/panel
https://abc1234.execute-api.us-east-1.amazonaws.com/dev/panel
```
If you use this database feature, you should also consider any privacy issues and have a plan for handling and storing riders' phone numbers outside of the Twilio service.

If you change any settings in the zappa_settings.json file, like adding database variables or setting a debug number (a 10-digit phone number that won't get saved to your database, for testing purposes), you can update your zappa deployment by running:
```
zappa update dev
```

## Authors

Angelo [@Trivisonno](https://twitter.com/Trivisonno) (not a professional app developer, so forgive all oversights)

## Version History

* 0.2 (in progress)
   * Correcting missing stop numbers in RTA data
   * Adding info for end of service situations such as Last Bus or No More Buses (evening/overnight situations) and re-routes.
* 0.1
    * Initial Release

## Known Issues
This app relies on GCRTA data from its NextConnect system and GTFS feeds. There are an extremely small number of identified errors that may cause some stop numbers not to return information. For example, Stop #00321 is on Route 1 (St. Clair) and is labeled [in the GTFS feed](https://transitfeeds.com/p/greater-cleveland-regional-transit-authority/214/latest/stop/00321) as **ST. CLAIR AV & E 153RD ST LOOP STOP 2**, but the NextConnect system does not have this stop simliarly labeled. (There is a stop labeled **E.153 & St. Clair Loop" (Published Stop)"** but it is not clear this is a match, or if this corresponds to **ST. CLAIR AV & E 153RD ST LOOP STOP 1** . It is not immediately clear how to search for arrival vehicles at this particular stop using GCRTA's NextConnect web page. Future work and updates will seek to understand these issues and eliminate any missing or mismatched data.

If this app is deployed on a large scale, additional steps will be required to ensure sufficient SMS throughput. With Twilio, 10-digit virtual numbers can only send one SMS message per second, so heavy instantaneous use will likely cause temporary SMS delivery delay. Other solutions exist, such as switching to a 5-digit shortcode number that allow higher SMS throughput, but this is not yet a focus of this project.


## License

This project is licensed under the Unlicense (Public Domain)- see the LICENSE file for details
