import os
import sys
import threading
import time

import dotenv
import paho.mqtt.client as mqtt
from gpiozero import Button

dotenv.load_dotenv()

BUTTON_PIN = 17
RATE_LIMIT = 1.0  # Minimum seconds between allowed clicks
ON_DURATION = 60  # Seconds to keep the button state ON after the last press

last_button_pressed = 0
mqttclient = mqtt.Client()
off_timer = None
state_lock = threading.Lock()


def on_mqtt_disconnect(client, userdata, rc=0):
    # Let systemd restart us
    print("mqtt disconnect")
    time.sleep(1)
    sys.exit(1)


def on_connect(client, userdata, flags, rc):
    print("Connected to mqtt")
    # Subscription is set up here to handle reconnects
    client.subscribe("hanpi/+")


def publish_off():
    global mqttclient, off_timer
    with state_lock:
        mqttclient.publish("hanpi/button", "OFF", retain=True)
        off_timer = None
        print("Published button off")


def button_pressed():
    global last_button_pressed, mqttclient, off_timer
    current_time = time.time()

    if current_time - last_button_pressed >= RATE_LIMIT:
        last_button_pressed = current_time
        mqttclient.publish("hanpi/button", "ON", retain=True)

        with state_lock:
            if off_timer is not None:
                off_timer.cancel()

            off_timer = threading.Timer(ON_DURATION, publish_off)
            off_timer.daemon = True
            off_timer.start()

        print("Published button press")
    else:
        print("Debounced button press")


def button_released():
    print("Button was released!")


def main() -> None:
    mqttclient.on_disconnect = on_mqtt_disconnect
    mqttclient.on_connect = on_connect
    mqttclient.tls_set()
    mqttclient.username_pw_set(os.getenv("MQTTS_USERNAME"), os.getenv("MQTTS_PASSWORD"))
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
        with state_lock:
            if off_timer is not None:
                off_timer.cancel()
        mqttclient.loop_stop()
        mqttclient.disconnect()


if __name__ == "__main__":
    main()
