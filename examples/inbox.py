#!/usr/bin/env python3

"""Example file for eternalegypt library."""

import sys
import asyncio
import aiohttp
import logging
import pprint

import eternalegypt

logging.basicConfig(level=logging.DEBUG)


async def get_information():
    """Example of printing the inbox."""
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)

    modem = eternalegypt.Modem(hostname=sys.argv[1], websession=websession)
    await modem.login(password=sys.argv[2])

    result = await modem.information()
    for sms in result.sms:
        pprint.pprint(sms)

    await modem.logout()
    await websession.close()

if len(sys.argv) != 3:
    print("{}: <netgear ip> <netgear password>".format(sys.argv[0]))
else:
    asyncio.get_event_loop().run_until_complete(get_information())
