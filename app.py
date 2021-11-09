from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import psycopg2 # uses pip install aws-psycopg2
# also pip install psycopg2-binary
import pytz
import json
import urllib.request
import datetime
import re
import boto3
import os
from datetime import timedelta

app = Flask(__name__)


# For local testing, must set environment variables
with open('zappa_settings.json','r', encoding='utf-8') as f:
    zappa_settings = json.loads(f.read())
    for k,v in zappa_settings['dev']['environment_variables'].items():
        os.environ[k]=v

# If the postgresql environment variables are empty, the app will skip the database functions
if os.environ.get('psycopg2_dbname') != "":
    conn = psycopg2.connect(dbname=os.environ.get('psycopg2_dbname'), port=os.environ.get('psycopg2_port'), user=os.environ.get('psycopg2_user'),
                                  password=os.environ.get('psycopg2_password'), host=os.environ.get('psycopg2_host'))
    cur = conn.cursor()
    # Create the database table if it does not already exist
    cur.execute("""CREATE TABLE IF NOT EXISTS rtatime (
          id int PRIMARY KEY NOT NULL,
          phone varchar NOT NULL,
          stop varchar NOT NULL,
          wkb_geometry geometry NOT NULL,
          t timestamp with time zone NOT NULL
        );""");
    conn.commit()


# The primary app function of sending an SMS reply with real-time vehicle arrival info.
@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
    with open('routesAtEachStop.json','r', encoding='utf-8') as f:
        routesAtEachStop = json.loads(f.read())

    with open('test-postedStopIDMapping.json', 'r', encoding='utf-8') as f:
        stopMap = json.loads(f.read())

    with open('test-rta_stops.geojson', 'r', encoding='utf-8') as f:
        rtaStops = json.loads(f.read())

    """Send a dynamic reply to an incoming text message"""
    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)
    phone = request.values.get('From', None)[-10:]

    # Start our TwiML response
    resp = MessagingResponse()

    mostCompressReturnText = {}

    stopNum = re.search(r"(?<!\d)\d{5}(?!\d)", body)
    if stopNum == None:
        resp.message('Please send only the five-digit stop number!')
        print('Please send only the five-digit stop number!')
        return str(resp)

    stopNum = stopNum.group()

    # First, we find the name of the transit stop using the sign's posted Stop #.
    try:
        rtaStopName = list(filter(lambda x:x["properties"]["stop_id"]==stopNum,rtaStops['features']))[0]['properties']['stop_name']
    except:
        resp.message("Sorry, we can't find that stop number! We will check with RTA and try to correct the error.")
        print("Sorry, we can't find that stop number! We will check with RTA and try to correct the error.")
        if os.environ.get('psycopg2_dbname') != "": saveToTable(lng, lat, phone, stop)
        return str(resp)

    # Second, we find the internal NextConnect system's stopID, which is different than the sign's posted Stop #.
    stopID = str(stopMap[stopNum])

    # Third, we find all of the routes that visit the transit stop.
    routeID = routesAtEachStop[stopID]

    # Next, we query GCRTA's NextConnect API for arrivals at the transit stop for each transit route.
    urlNextConnect = 'http://nextconnect.riderta.com/Arrivals.aspx/getStopTimes'

    for route in routeID.split('_'):
        params = json.dumps({"routeID": route.split('-')[0], "directionID": route.split('-')[1], "stopID": stopID, "tpID": 0, "useArrivalTimes": "false"}).encode('utf8')
        req = urllib.request.Request(urlNextConnect, data=params,
                                     headers={'content-type': 'application/json'})
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf8'))

        try: # I hate this try loop here, but is necessary ATM for when certain routes have no more buses after late night and ['crossings'] is NoneType
            for stop in data['d']['routeStops'][0]['stops'][0]['crossings']:
                try:
                    stop['schedHr24'] = datetime.datetime.strftime(datetime.datetime.strptime(stop['schedTime']+stop['schedPeriod'], "%I:%M%p"), "%H%M")
                    stop['predHr24'] = datetime.datetime.strftime(datetime.datetime.strptime(stop['predTime']+stop['predPeriod'], "%I:%M%p"), "%H%M")
                    eta = int(stop['schedHr24'])-int(stop['predHr24'])


                    if (eta < 0):
                        stop['eta'] = str(eta)+" min"
                    else:
                        stop['eta'] = "On time"
                except:
                    pass

                stop['ampmNow'] = (datetime.datetime.now()-datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=5, weeks=0)).strftime("%p").lower()
                if (stop['ampmNow']=="pm" and stop['schedPeriod']=="am"):
                    stop['schedHr24ordered'] = str(int(stop['schedHr24'])+2400)
                else:
                    stop['schedHr24ordered'] = stop['schedHr24']


                # mostCompressReturnText
                try:
                    if stop['predTime']!=None:
                        mostCompressReturnText[stop['destination'].split(' ')[0]] = mostCompressReturnText[stop['destination'].split(' ')[0]] + ', ' + stop['predTime'].replace(":","") + stop['predPeriod'][0]
                    else:
                        mostCompressReturnText[stop['destination'].split(' ')[0]] = mostCompressReturnText[stop['destination'].split(' ')[0]] + ', ' + stop['schedTime'].replace(":","") + stop['schedPeriod'][0]
                except:
                    if stop['predTime']!=None:
                        mostCompressReturnText[stop['destination'].split(' ')[0]] = stop['predTime'].replace(":","") + stop['predPeriod'][0]
                    else:
                        mostCompressReturnText[stop['destination'].split(' ')[0]] = stop['schedTime'].replace(":","") + stop['schedPeriod'][0]

                if 'eta' in stop.keys():
                    if stop['eta'] != "On time":
                        mostCompressReturnText[stop['destination'].split(' ')[0]] = mostCompressReturnText[stop['destination'].split(' ')[0]]# + ' (' + stop['eta'].replace('-','') + ')'
        except:
            pass


    # mostCompressReturnText
    mostCompressReturnTextString = rtaStopName + "\n"
    mostCompressReturnText = dict(sorted(mostCompressReturnText.items()))
    for k, v in mostCompressReturnText.items():
        #print(k+': '+v.strip())
        mostCompressReturnTextString = mostCompressReturnTextString + k+': '+v.strip() + '\n'
    if len(mostCompressReturnText)==0:
        mostCompressReturnTextString = mostCompressReturnTextString +('No more stops here tonight.')
    print(mostCompressReturnTextString)
    mostCompressReturnTextString = mostCompressReturnTextString.strip()
    resp.message(mostCompressReturnTextString)

    if os.environ.get('psycopg2_dbname') != "":
        rtaStopCoordLat, rtaStopCoordLng = list(filter(lambda x:x["properties"]["stop_id"]==stopNum,rtaStops['features']))[0]['geometry']['coordinates'][1], list(filter(lambda x:x["properties"]["stop_id"]==stopNum,rtaStops['features']))[0]['geometry']['coordinates'][0]
        lat, lng, phone, stop = rtaStopCoordLat, rtaStopCoordLng, phone, stopNum

        if phone != os.environ.get('debug_phone_number')[-10:]:
            saveToTable(lng, lat, phone, stop)

    return str(resp)

# If the postgresql environment variables are empty, then the panel features are disabled.
@app.route("/panel", methods=['GET', 'POST'])
def panel():
    if os.environ.get('psycopg2_dbname') != "":
        return 'Database features disabled.'

    with open('test-rta_stops.geojson', 'r', encoding='utf-8') as f:
        rtaStops = json.loads(f.read())

    results = getAllFromTable()

    newResults = []
    for result in results:
        newResult = list(result)
        rtaStopName = list(filter(lambda x:x["properties"]["stop_id"]==result[2],rtaStops['features']))[0]['properties']['stop_name']
        newResult.append(rtaStopName)
        newResults.append(newResult)

    client = Client(os.environ.get('twilio_account_sid'), os.environ.get('twilio_auth_token'))
    balance_data = client.api.v2010.balance.fetch()
    balance = float(balance_data.balance)

    return render_template('panel.html', results=newResults, balance=balance)


# If the postgresql environment variables are empty, then the panel features are disabled.
@app.route("/status/<sms>/", methods=['GET', 'POST'])
def status(sms):
    if os.environ.get('psycopg2_dbname') != "":
        return 'Database features disabled.'

    from datetime import datetime
    client = Client(os.environ.get('twilio_account_sid'), os.environ.get('twilio_auth_token'))

    results = getOneFromTable()
    timeafter = results[0][0]
    timebefore = results[0][0] + timedelta(seconds=1)
    tz = pytz.timezone('America/New_York')

    messages = client.messages.list(
                                   date_sent_after=timeafter,
                                   date_sent_before=timebefore,
                                   to=results[0][1],
                                   limit=20
                               )

    sid = record.sid
    timestring = results[0][0].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S %A')
    bodystring = messages[0].body.replace('\n','<br>')
    price = messages[0].price if messages[0].price != None else '?'
    numsegments = messages[0].num_segments
    numchars = str(len(messages[0].body))

    return sid+"<br>(" + timestring + ")<br><br>"+bodystring+'<br><br>Cost: '+ price+" ("+numsegments+" segments, "+ numchars + " chars)"


def saveToTable(lng, lat, phone, stop):
    cur.execute("SET timezone = 'America/New_York'; INSERT INTO rtatime(wkb_geometry, phone, stop, t) VALUES (ST_SetSRID(ST_MakePoint(%s, %s),4326), %s, %s, NOW());", (lng, lat, phone, stop))
    conn.commit()


def getOneFromTable(sms):
    cur.execute("SELECT t, phone FROM rtatime WHERE id=%s", (sms, ))
    return cur.fetchall()


def getAllFromTable():
    cur.execute("SELECT *, ST_X(wkb_geometry) as lat, ST_Y(wkb_geometry) as lng FROM rtatime ORDER BY t DESC")
    return cur.fetchall()
