import asyncio
import os
import sys
from datetime import datetime

import aiofiles
from hbmqtt.client import MQTTClient

CERTFILE = os.path.expanduser("~/Projects/mqtt_certs/ca.crt")
# PATH = "/sys/devices/platform/unipi_plc/io_group2/di_2_01/di_value"
PATH = os.path.expanduser("~/Projects/unipoll/test.md")
INTERVAL = 500e-3


class DigitalInput:
    TRUE_VALUE = "1\n"
    FALSE_VALUE = "0\n"

    def __init__(self, path, topic, callback, value=False):
        self.path = path
        self.topic = topic
        self.callback = callback
        self._value = value

    async def update(self):
        """update internal value with latest"""
        async with aiofiles.open(self.path, "r") as fh:
            updated = await fh.read() == DigitalInput.TRUE_VALUE
        if updated != self._value:
            if not self._value:
                self.callback(self)
            self._value = updated


async def poll(client):
    async def callback(digital_input):
        await client.publish(digital_input.topic, payload=str(datetime.now()))

    digital_input = DigitalInput(PATH, "di_2_01", callback)
    di2 = DigitalInput(PATH, "buzz", callback)
    while True:
        asyncio.gather(digital_input.update(), di2.update())
        await asyncio.sleep(INTERVAL)


def main():
    client = MQTTClient()
    client.tls_set(CERTFILE)
    client.connect("raspberrypi.lan", 8883)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(poll(client))
    loop.close()


if __name__ == "__main__":
    sys.exit(main())
