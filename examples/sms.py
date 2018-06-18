#!/usr/bin/env python3

"""Example file for Eternal Egypt library."""

import sys
import asyncio
import aiohttp
import logging

import eternalegypt

logging.basicConfig(level=logging.DEBUG)


async def send_message():
    """Example of sending a message."""
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)

    modem = eternalegypt.LB2120(websession=websession)
    await modem.login(hostname=sys.argv[1], password=sys.argv[2])

    await modem.sms(phone=sys.argv[3], message=sys.argv[4])

    await websession.close()

if len(sys.argv) != 5:
    print("{}: <lb2120 ip> <lb2120 password> <phone> <message>".format(
        sys.argv[0]))
else:
    asyncio.get_event_loop().run_until_complete(send_message())
