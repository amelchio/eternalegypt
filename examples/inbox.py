#!/usr/bin/env python3

"""Example file for LB2120 library."""

import sys
import asyncio
import logging
import pprint

import eternalegypt

logging.basicConfig(level=logging.DEBUG)


async def get_information():
    """Example of printing the inbox."""
    modem = eternalegypt.LB2120(
        hostname=sys.argv[1],
        password=sys.argv[2])

    result = await modem.information()
    for sms in result.sms:
        pprint.pprint(sms)

if len(sys.argv) != 3:
    print("{}: <lb2120 ip> <lb2120 password>".format(sys.argv[0]))
else:
    asyncio.get_event_loop().run_until_complete(get_information())
