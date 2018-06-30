#!/usr/bin/env python3

"""Example file for LB2120 library."""

import sys
import asyncio
import aiohttp
import logging

import eternalegypt

logging.basicConfig(level=logging.DEBUG)


async def get_information():
    """Example of printing the current upstream."""
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)

    modem = eternalegypt.Modem(hostname=sys.argv[1], websession=websession)
    await modem.login(password=sys.argv[2])

    result = await modem.information()
    print("Upstream: {}".format(result.upstream))

    await modem.logout()
    await websession.close()

if len(sys.argv) != 3:
    print("{}: <lb2120 ip> <lb2120 password>".format(sys.argv[0]))
else:
    asyncio.get_event_loop().run_until_complete(get_information())
