import asyncio
import os
import sys

import aiofiles
import paho.mqtt.client as mqtt

CERTFILE = os.path.expanduser("~/Projects/mqtt_certs/ca.crt")
PATH = "/sys/devices/platform/unipi_plc/io_group1/di_1_01"
INTERVAL = 0.5


class DigitalInput:
    TRUE_VALUE = "1"
    FALSE_VALUE = "0"

    def __init__(self, path, topic, callback, value=False):
        self.path = path
        self.topic = topic
        self.callback = callback
        self._value = value

    async def update(self):
        """update internal value with latest"""
        async with aiofiles.open(self.path, "r") as fh:
            updated = await fh.read() == DigitalInput.TRUE_VALUE
            if updated != self.value:
                self.callback(self)


async def poll(client):
    def callback(digital_input):
        client.publish(digital_input.topic, payload="test")

    digital_input = DigitalInput(PATH, "di_1_01", callback)
    while True:
        await digital_input.update()
        asyncio.sleep(INTERVAL)


def main(self):
    client = mqtt.Client()
    client.tls_set(certfile=CERTFILE)
    client.connect("raspberrypi.lan", 8883)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(poll(client))
    loop.close()


if __name__ == "__main__":
    sys.exit(main())
