#!/usr/bin/env python3

"""Example file for eternalegypt library."""

import sys
import asyncio
import aiohttp

import eternalegypt

import logging
#logging.basicConfig(level=logging.DEBUG)

async def provision(op_mode="bridge"):
    """Example of provisioning to set APN, operation mode (default bridge) and output IMEI,ICCID for activation"""
    jar = aiohttp.CookieJar(unsafe=True)
    websession = aiohttp.ClientSession(cookie_jar=jar)
    imei = None
    iccid = None
    retval = 0
    try:
        modem = eternalegypt.Modem(hostname=sys.argv[1], websession=websession)
        await modem.login(password=sys.argv[2])
        result = await modem.information()
        imei = result.items.get("general.imei")
        iccid = result.items.get("sim.iccid")
        if iccid is None:
            print("Cannot retrieve ICCID, check SIM", file=sys.stderr)
            retval = 1
        else:
            apn = result.items.get("wwan.profilelist.0.apn")
            if apn != sys.argv[3]:
                print(f"Setting APN to {sys.argv[3]}, restart provisioning after reboot", file=sys.stderr)
                await modem.set_apn(apn=sys.argv[3])
                retval = 2
            else:
                ippassthroughenabled = result.items.get("router.ippassthroughenabled")
                bridgemode = True if op_mode == "bridge" else False
                if ippassthroughenabled != bridgemode:
                    print(f"Setting bridge mode to {bridgemode}, restart provisioning after reboot", file=sys.stderr)
                    await modem.set_ip_pass_through_enabled(ipPassThroughEnabled=bridgemode)
                    retval = 3
    except Exception as ex:
        print(f"Execption raised: {ex}", file=sys.stderr)
        print("Provisioning aborted", file=sys.stderr)
        retval = 4
    await modem.logout()
    await websession.close()
    print(f"{imei},{iccid}") # output csv: IMEI,ICCID
    return retval

if len(sys.argv) != 5:
    print("{}: <netgear ip> <netgear password> <apn> <operation mode>".format(sys.argv[0]), file=sys.stderr)
    sys.exit(255)
else:
    op_mode = sys.argv[4].lower()
    if op_mode not in ("bridge", "router"):
        print("Values for <operation mode> must be 'bridge' or 'router'")
        sys.exit(254)
    sys.exit(asyncio.run(provision(op_mode=op_mode)))
