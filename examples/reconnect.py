#!/usr/bin/env python3

"""Example file for eternalegypt library."""

import sys
import asyncio
import aiohttp

import eternalegypt

import logging
logging.basicConfig(level=logging.DEBUG)

async def reconnect():
    """Example of disconnecting and reconnecting."""
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)

    modem = eternalegypt.Modem(hostname=sys.argv[1], websession=websession)
    await modem.login(password=sys.argv[2])

    print("Disconnecting")
    await modem.disconnect_lte()

    print("Waiting 5 seconds")
    await asyncio.sleep(5)

    print("Connecting")
    await modem.connect_lte()

    print("Waiting 5 seconds")
    await asyncio.sleep(5)

    print("Closing down")
    await modem.logout()
    await websession.close()

if len(sys.argv) != 3:
    print("{}: <netgear ip> <netgear password>".format(sys.argv[0]))
else:
    asyncio.get_event_loop().run_until_complete(reconnect())
