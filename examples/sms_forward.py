#!/usr/bin/env python3

"""Example file for Eternal Egypt library."""

import sys
import asyncio
import aiohttp
import logging

import eternalegypt


async def wait_for_messages():
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)

    modem = eternalegypt.Modem(hostname=sys.argv[1], websession=websession)
    await modem.login(password=sys.argv[2])
    def forward_sms(sms):
        if sms.sender == sys.argv[3]:
            phone, message = sms.message.split(": ", 1)
            asyncio.get_event_loop().create_task(modem.sms(phone=phone, message=message))
        else:
            asyncio.get_event_loop().create_task(modem.sms(phone=sys.argv[3], message=f"{sms.sender}: {sms.message}"))
    await modem.add_sms_listener(forward_sms)

    try:
        while True:
            await modem.information() # sends new sms objects to listener
            await asyncio.sleep(5)
    finally:
        await modem.logout()
        await websession.close()

if len(sys.argv) != 4:
    print("{}: <netgear ip> <netgear password> <phone>".format(sys.argv[0]))
else:
    asyncio.get_event_loop().run_until_complete(wait_for_messages())
