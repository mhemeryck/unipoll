import argparse
import asyncio
import logging
import os
import re
import sys

import aiofiles
from hbmqtt.client import MQTTClient

logger = logging.getLogger(__name__)

# Default async waiting interval
SLEEP_INTERVAL = 500e-3
# unipi sysfs root folder where to find all digital inputs
SYSFS_ROOT = "/sys/devices/platform/unipi_plc"


class DigitalInput:
    TRUE_VALUE = "1\n"
    FALSE_VALUE = "0\n"
    FOLDER_REGEX = re.compile(r"di_\d_\d{2}")
    _DI_VALUE_FILE = "di_value"

    def __init__(self, path, client, topic=None, value=False):
        self.path = path
        self.client = client
        self.topic = topic or DigitalInput._topic_from_path(path)
        self._value = value

    @classmethod
    def _topic_from_path(cls, path):
        """If not topic is specified, just discern it from the path"""
        match = DigitalInput.FOLDER_REGEX.search(path)
        start, end = match.span()
        return path[start:end]

    @property
    def _di_value_path(self):
        return os.path.join(self.path, DigitalInput._DI_VALUE_FILE)

    async def update(self):
        """update internal value with latest"""
        # Read the contents
        async with aiofiles.open(self._di_value_path, "r") as fh:
            updated = await fh.read() == DigitalInput.TRUE_VALUE

        # Check for updates
        if updated != self._value:
            # In case of leading edge, trigger
            if not self._value:
                logger.info("Input toggle for %s", self.topic)
                await self.client.publish(self.topic, b"test_message")
            # Update the value
            self._value = updated


async def poll(digital_inputs, sleep_time):
    while True:
        asyncio.gather(*[digital_input.update() for digital_input in digital_inputs])
        await asyncio.sleep(sleep_time)


def find_digital_input_paths(folder, regex=DigitalInput.FOLDER_REGEX):
    """Crawl root folder for digital input files"""
    paths = []
    for root, dirs, files in os.walk(folder):
        for d in dirs:
            match = regex.match(d)
            if match is not None:
                paths.append(os.path.join(root, d))
    return paths


def create_digital_inputs(root, client):
    paths = find_digital_input_paths(root)
    return [DigitalInput(path, client) for path in paths]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("uri", help="MQTT broker URI")
    parser.add_argument("--cafile", help="Optional path to CA file for MQTT over TLS")
    parser.add_argument(
        "--sleep", type=float, default=SLEEP_INTERVAL, help="Sleep time between updates"
    )
    parser.add_argument(
        "--sysfs_root",
        default=SYSFS_ROOT,
        help="sysfs root folder to scan for digital inputs",
    )
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    # Create MQTT client
    client = MQTTClient()
    loop.run_until_complete(client.connect(args.uri, cafile=args.cafile))

    # Digital inputs
    digital_inputs = create_digital_inputs(SYSFS_ROOT, client)

    loop.run_until_complete(poll(digital_inputs, args.sleep))
    loop.close()


if __name__ == "__main__":
    sys.exit(main())
