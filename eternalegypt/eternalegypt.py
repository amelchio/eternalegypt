"""Library for interfacing with Netgear LTE modems."""
import logging
import re
import json
import datetime
import aiohttp
import async_timeout
import attr

_LOGGER = logging.getLogger(__name__)

@attr.s
class SMS:
    id = attr.ib()
    timestamp = attr.ib()
    unread = attr.ib()
    sender = attr.ib()
    message = attr.ib()

@attr.s
class Information:
    sms = attr.ib(factory=list)
    usage = attr.ib(default=None)

class LB2120:
    """Class for Netgear LB2120 interface."""

    def __init__(self, hostname, password):
        """Initialize the object."""
        self.baseurl = "http://{}/".format(hostname)
        self.password = password
        self.token = None

    def url(self, path):
        """Build a complete URL for the device."""
        return self.baseurl + path

    async def login(self):
        jar = aiohttp.CookieJar(unsafe=True)
        session = aiohttp.ClientSession(cookie_jar=jar)

        async with async_timeout.timeout(10):
            url = self.url('index.html')
            async with session.get(url) as response:
                text = await response.text()
                self.token = re.search(r'name="token" value="(.*?)"', text).group(1)
                _LOGGER.debug("Token: %s", self.token)

            url = self.url('Forms/config')
            data = {
                'session.password': self.password,
                'token': self.token
            }
            async with session.post(url, data=data) as response:
                _LOGGER.debug("Got cookie with status %d", response.status)

            return session

    async def sms(self, phone, message):
        """Send a message."""
        session = await self.login()
        _LOGGER.debug("Send to %s via %s len=%d",
                      phone, self.baseurl, len(message))

        async with async_timeout.timeout(10):
            url = self.url('Forms/smsSendMsg')
            data = {
                'sms.sendMsg.receiver': phone,
                'sms.sendMsg.text': message,
                'sms.sendMsg.clientId': __name__,
                'action': 'send',
                'token': self.token
            }
            async with session.post(url, data=data) as response:
                _LOGGER.debug("Sent message with status %d", response.status)

        await session.close()

    async def information(self):
        """Return the SMS inbox."""
        session = await self.login()
        result = Information()

        async with async_timeout.timeout(10):
            url = self.url('model.json')
            async with session.get(url) as response:
                data = json.loads(await response.text())

                result.usage = data['wwan']['dataUsage']['generic']['dataTransferred']

                for msg in [m for m in data['sms']['msgs'] if 'text' in m]:
                    # {'id': '6', 'rxTime': '11/03/18 08:18:11 PM', 'text': 'tak tik', 'sender': '555-987-654', 'read': False}
                    dt = datetime.datetime.strptime(msg['rxTime'], '%d/%m/%y %I:%M:%S %p')
                    element = SMS(int(msg['id']), dt, not msg['read'], msg['sender'], msg['text'])
                    result.sms.append(element)
                result.sms.sort(key=lambda sms:sms.id)

        await session.close()

        return result
