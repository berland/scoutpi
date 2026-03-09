import glob
import logging
from datetime import datetime, timezone
import dotenv
import os
import sys
import time

import paho.mqtt.client as mqtt

import json
import urllib.request


logger = logging.getLogger("scout-pi")
dotenv.load_dotenv()

# Initialize the 1-Wire interface
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Locate the sensor file
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def send_trace(message: str, severity: str = "Information", properties: dict = None):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    envelope = {
        "name": "Microsoft.ApplicationInsights.Message",
        "time": ts,
        "iKey": INSTRUMENTATION_KEY,
        "tags": {
            "ai.cloud.roleInstance": "scout-pi",
        },
        "data": {
            "baseType": "MessageData",
            "baseData": {
                "ver": 2,
                "message": message,
                "severityLevel": severity, 
                "properties": properties or {},
            }
        }
    }

    body = json.dumps(envelope).encode("utf-8")

    req = urllib.request.Request(
        AZURE_URL ,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return r.status

class AppInsightsHandler(logging.Handler):
    def emit(self, record):
        try:
            send_trace(
                message=self.format(record),
                severity="Information",
                properties={
                    "logger":   record.name,
                }
            )
        except Exception:
            self.handleError(record)

def parse_azure_connection_string() -> tuple[str, str]:
    """Returns the key and the url to post to in a tuple"""
    dotenv.load_dotenv()
    conn_str = os.getenv("AZURE_CONNECTION_STRING")
    assert conn_str
    parsed = dict(part.split("=", 1) for part in conn_str.split(";") if "=" in part)
    return (parsed["InstrumentationKey"], parsed["IngestionEndpoint"].rstrip("/") + "/v2/track")

INSTRUMENTATION_KEY, AZURE_URL = parse_azure_connection_string()

def on_mqtt_disconnect(client, userdata, rc=0):
    # Let systemd restart us
    time.sleep(1)
    sys.exit(1)

def on_connect(client, userdata, flags, rc):
    print("Connected to mqtt")
    # Subscription is set up here to handle reconnects
    client.subscribe("hanpi/+")

def read_temp_raw() -> str:
    with open(device_file, 'r') as f:
        return f.readlines()

def read_temp() -> float:
    lines = read_temp_raw()
    # Wait for a valid reading (indicated by 'YES')
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    
    # Extract temperature from the second line
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def main() -> None:
    mqttclient = mqtt.Client()
    mqttclient.on_disconnect = on_mqtt_disconnect
    mqttclient.on_connect = on_connect
    mqttclient.tls_set()
    mqttclient.username_pw_set(os.getenv("MQTTS_USERNAME"), os.getenv("MQTTS_PASSWORD"))
    mqttclient.connect(os.getenv("MQTTS_HOST"), int(os.getenv("MQTTS_PORT")))
    mqttclient.loop(2)  # Give time to connect

    logger.setLevel(logging.INFO)
    logger.addHandler(AppInsightsHandler())
    
    
    last_published_temp : float = -99.0 
    while True:
        celsius = read_temp()
        print(f"Temp: {celsius:.2f}°C")
        
        rounded_temp = f"{celsius:.2f}"
        if abs(celsius - last_published_temp) > 0.1:
            print("publishing significant change")
            mqttclient.publish(f"{os.getenv('MQTTS_BASETOPIC')}/temperature", rounded_temp)
            logger.info({"temperature_CU13B": rounded_temp})
            last_published_temp = celsius 
        time.sleep(2)

if __name__ == "__main__":
    main()
    
