import sys
import time
import os

import paho.mqtt.client as mqtt
from gpiozero import Button
import dotenv

dotenv.load_dotenv()

BUTTON_PIN = 17
RATE_LIMIT = 1.0  # Minimum seconds between allowed clicks

last_button_pressed = 0
mqttclient = mqtt.Client()


def on_mqtt_disconnect(client, userdata, rc=0):
    # Let systemd restart us
    print("mqtt disconnect")
    time.sleep(1)
    sys.exit(1)

def on_connect(client, userdata, flags, rc):
    print("Connected to mqtt")
    # Subscription is set up here to handle reconnects
    client.subscribe("hanpi/+")

def button_pressed():
    global last_button_pressed, mqttclient
    current_time = time.time()
    
    if current_time - last_button_pressed >= RATE_LIMIT:
        mqttclient.publish("hanpi/button", "ON")
        last_button_pressed = current_time
        print("Published button press")
    else:
        print("Debounced button press")

def button_released():
    print("Button was released!")

def main() -> None:
    mqttclient.on_disconnect = on_mqtt_disconnect
    mqttclient.on_connect = on_connect
    mqttclient.tls_set()
    mqttclient.username_pw_set(os.getenv("MQTTS_USER"), os.getenv("MQTTS_PASSWORD"))
    mqttclient.connect(os.getenv("MQTTS_HOST"), int(os.getenv("MQTTS_PORT")))
    mqttclient.loop(2)  # Give time to connect

    # Initialize button on GPIO 17
    # 'pull_up=True' (default) means the pin is HIGH until pressed
    button = Button(BUTTON_PIN)

    # Assign functions to events
    button.when_pressed = button_pressed
    button.when_released = button_released
    try:
        print("ready")
        mqttclient.loop_forever()
    except KeyboardInterrupt:
        mqttclient.loop_stop()
        mqttclient.disconnect()

if __name__ == "__main__":
    main()
