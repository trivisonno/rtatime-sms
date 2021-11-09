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
* Assumes knowledge of command-line.


### Installing

* Clone the repo into your local directory for testing
* Create a pipenv for your pip packages such as flask and/or zappa
```
git clone https://www.github.com/trivisonno/rtatime-sms
cd rtatime-sms
pipenv shell --python 3.8
pip install flask zappa twilio
```

If using the optional database, also install psycopg2 and timezone/pytz modules:
```
pip install aws-psycopg2 psycopg2-binary pytz
```

To test locally:
```
export FLASK_APP=app.py
flask run
```

Try a 5-digit stop number (Stop # 03457 as example) in the Body parameter and include a 10-digit phone number in the From parameter:
```
http://127.0.0.1:5000/sms?Body=03457&From=+15555555555
```

If you have an AWS account set up and are ready to deploy to AWS Lambda for real-world use, then deploy with zappa:
```
$ pip install zappa
$ zappa init
$ zappa deploy dev
```

Zappa will automatically create an API Gateway URL for you to use as a Webhook with the Twilio messaging system. Your URL should end in /sms, like below
```
https://abc1234.execute-api.us-east-1.amazonaws.com/dev/sms
```

Once deployed to AWS, you can test easily from your browser by trying
```
https://abc1234.execute-api.us-east-1.amazonaws.com/dev/sms?Body=03457&From=+15555555555
```

Both will return text for an SMS reply message.
```
DETROIT AV & W 65TH ST
26: 1131a, 1147a
26A: 1117a
```

If you choose to use the database features to track app usage, then there is also a Dashboard panel provided that can be accessed at:
```
http://127.0.0.1:5000/panel
https://abc1234.execute-api.us-east-1.amazonaws.com/dev/panel
```
If you use this database feature, you should also consider any privacy issues and have a plan for handling and storing riders' phone numbers outside of the Twilio service.


### Connecting to Twilio
After deploying your SMS app to the cloud, you will configure Twilio to send a POST request to your API Gateway URL upon receipt of an SMS message from a user. Visit your Twilio console and navigate to the [Manage Active Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/active) page and select the virtual phone number for the app. Add your AWS API Gateway link in the messaging section under the "When A Message Comes In" setting and select HTTP POST and Webhook. Now, SMS message data will be forwarded to your app for a reply with the arrival info.


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
