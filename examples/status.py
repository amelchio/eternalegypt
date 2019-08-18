#!/usr/bin/env python3

"""Example file for eternalegypt library."""

import sys
import asyncio
import aiohttp

import eternalegypt

async def get_information():
    """Example of printing the current upstream."""
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)

    try:
        modem = eternalegypt.Modem(hostname=sys.argv[1], websession=websession)
        await modem.login(password=sys.argv[2])

        result = await modem.information()
        if len(sys.argv) == 3:
            print("serial_number: {}".format(result.serial_number))
            print("usage: {}".format(result.usage))
            print("upstream: {}".format(result.upstream))
            print("wire_connected: {}".format(result.wire_connected))
            print("mobile_connected: {}".format(result.mobile_connected))
            print("connection_text: {}".format(result.connection_text))
            print("connection_type: {}".format(result.connection_type))
            print("current_nw_service_type: {}".format(result.current_nw_service_type))
            print("current_ps_service_type: {}".format(result.current_ps_service_type))
            print("register_network_display: {}".format(result.register_network_display))
            print("roaming: {}".format(result.roaming))
            print("radio_quality: {}".format(result.radio_quality))
            print("rx_level: {}".format(result.rx_level))
            print("tx_level: {}".format(result.tx_level))
            print("current_band: {}".format(result.current_band))
            print("cell_id: {}".format(result.cell_id))
        else:
            key = sys.argv[3]
            print("{}: {}".format(key, result.items.get(key)))

        await modem.logout()
    except eternalegypt.Error:
        print("Could not login")

    await websession.close()

if len(sys.argv) not in (3, 4):
    print("{}: <netgear ip> <netgear password> [key]".format(sys.argv[0]))
else:
    asyncio.get_event_loop().run_until_complete(get_information())
