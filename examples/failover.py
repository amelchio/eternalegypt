#!/usr/bin/env python3

"""Example file for eternalegypt library."""

import sys
import asyncio
import aiohttp
import logging

import eternalegypt

async def set_failover_mode(mode):
    """Example of printing the current upstream."""
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)

    try:
        modem = eternalegypt.Modem(hostname=sys.argv[1], websession=websession)
        await modem.login(password=sys.argv[2])

        await modem.set_failover_mode(mode)

        await modem.logout()
    except eternalegypt.Error:
        print("Could not login")

    await websession.close()

if len(sys.argv) != 4:
    print("{}: <netgear ip> <netgear password> <mode>".format(sys.argv[0]))
else:
    asyncio.run(set_failover_mode(sys.argv[3]))
