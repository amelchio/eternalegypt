"""Library for interfacing with Netgear LTE modems."""
import logging
import re
import json
import datetime
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

@attr.s
class LB2120:
    """Class for Netgear LB2120 interface."""

    hostname = attr.ib()
    websession = attr.ib()

    token = attr.ib(init=False)

    @property
    def baseurl(self):
        return "http://{}/".format(self.hostname)

    def url(self, path):
        """Build a complete URL for the device."""
        return self.baseurl + path

    async def login(self, password):
        async with async_timeout.timeout(10):
            url = self.url('index.html')
            async with self.websession.get(url) as response:
                text = await response.text()
                try:
                    self.token = re.search(r'name="token" value="(.*?)"', text).group(1)
                except Exception:
                    print(response.headers)
                _LOGGER.debug("Token: %s", self.token)

            url = self.url('Forms/config')
            data = {
                'session.password': password,
                'token': self.token
            }
            async with self.websession.post(url, data=data) as response:
                _LOGGER.debug("Got cookie with status %d", response.status)

    async def sms(self, phone, message):
        """Send a message."""
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
            async with self.websession.post(url, data=data) as response:
                _LOGGER.debug("Sent message with status %d", response.status)

    async def delete_sms(self, sms_id):
        """Delete a message."""

        async with async_timeout.timeout(10):
            url = self.url('Forms/config')
            data = {
                'sms.deleteId': sms_id,
                'err_redirect': '/error.json',
                'ok_redirect': '/success.json',
                'token': self.token
            }
            async with self.websession.post(url, data=data) as response:
                _LOGGER.debug("Delete %d with status %d", sms_id, response.status)

    async def information(self):
        """Return the SMS inbox."""
        result = Information()

        async with async_timeout.timeout(10):
            url = self.url('model.json')
            async with self.websession.get(url) as response:
                data = json.loads(await response.text())

                result.usage = data['wwan']['dataUsage']['generic']['dataTransferred']

                for msg in [m for m in data['sms']['msgs'] if 'text' in m]:
                    # {'id': '6', 'rxTime': '11/03/18 08:18:11 PM', 'text': 'tak tik', 'sender': '555-987-654', 'read': False}
                    dt = datetime.datetime.strptime(msg['rxTime'], '%d/%m/%y %I:%M:%S %p')
                    element = SMS(int(msg['id']), dt, not msg['read'], msg['sender'], msg['text'])
                    result.sms.append(element)
                result.sms.sort(key=lambda sms:sms.id)

        return result

class Modem(LB2120):
    """Class for any modem."""
