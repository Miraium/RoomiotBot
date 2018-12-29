#coding: utf-8

import os
import urllib.request, urllib.parse, urllib.error
import json

my_thingspeak_apikey_sensor = os.getenv('THINGSPEAK_APIKEY_SENSOR', None)
my_thingspeak_channel_sensor = os.getenv('THINGSPEAK_CHANNEL_SENSOR', None)

my_thingspeak_apikey_state = os.getenv('THINGSPEAK_APIKEY_STATE', None)
my_thingspeak_channel_state = os.getenv('THINGSPEAK_CHANNEL_STATE', None)

url_template_write = "https://api.thingspeak.com/update?api_key={api_key}&field1={state}"
url_template_read = "https://api.thingspeak.com/channels/{channel}/feeds.json?api_key={api_key}&results={num_result}"

num_result = 1
url_template = "https://api.thingspeak.com/channels/{channel}/feeds.json?api_key={api_key}&results={num_result}"

def get_environment_field():
    url = url_template.format(channel=my_thingspeak_channel_sensor, api_key=my_thingspeak_apikey_sensor, num_result=num_result)
    result = urllib.request.urlopen(url).read()
    data = json.loads(result)
    feeds = data.get("feeds")
    latest_feed = feeds[0]

    time = latest_feed.get("created_at")
    temperature = latest_feed.get("field1")
    pressure = latest_feed.get("field2")
    humidity = latest_feed.get("field3")

    fields = {
        "time": time,
        "temperature": temperature,
        "pressure": pressure,
        "humidity": humidity
    }

    return fields

def read_current_state():
    num_result = 1
    url = url_template_read.format(channel=my_thingspeak_channel_state, api_key=my_thingspeak_apikey_state, num_result=num_result)
    result = urllib.request.urlopen(url).read()
    data = json.loads( result )
    feeds = data.get("feeds")
    latest_feed = feeds[0]
    return latest_feed.get("field1")

def write_current_state(state_to_write):
    url = url_template_write.format(api_key=my_thingspeak_apikey_state, state=state_to_write)
    result = urllib.request.urlopen(url).read()

if __name__ == "__main__":
    fields = get_environment_field()
    print(fields)