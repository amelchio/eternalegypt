"""Library for interfacing with Netgear LTE modems."""
import logging
import re
import json
from functools import wraps
from datetime import datetime
import asyncio
from aiohttp.client_exceptions import ClientError
import async_timeout
import attr

TIMEOUT = 3

_LOGGER = logging.getLogger(__name__)


class Error(Exception):
    """Base class for all exceptions."""


@attr.s
class SMS:
    """An SMS message."""
    id = attr.ib()
    timestamp = attr.ib()
    unread = attr.ib()
    sender = attr.ib()
    message = attr.ib()


@attr.s
class Information:
    """Various information from the modem."""
    sms = attr.ib(factory=list)
    usage = attr.ib(default=None)
    upstream = attr.ib(default=None)
    serial_number = attr.ib(default=None)
    connection = attr.ib(default=None)
    connection_text = attr.ib(default=None)
    connection_type = attr.ib(default=None)
    current_nw_service_type = attr.ib(default=None)
    current_ps_service_type = attr.ib(default=None)
    register_network_display = attr.ib(default=None)
    roaming = attr.ib(default=None)
    radio_quality = attr.ib(default=None)
    rx_level = attr.ib(default=None)
    tx_level = attr.ib(default=None)
    current_band = attr.ib(default=None)
    cell_id = attr.ib(default=None)


def autologin(function, timeout=TIMEOUT):
    """Decorator that will try to login and redo an action before failing."""
    @wraps(function)
    async def wrapper(self, *args, **kwargs):
        """Wrap a function with timeout."""
        try:
            async with async_timeout.timeout(timeout):
                return await function(self, *args, **kwargs)
        except (asyncio.TimeoutError, ClientError, Error):
            pass

        _LOGGER.debug("autologin")
        try:
            async with async_timeout.timeout(timeout):
                await self.login()
                return await function(self, *args, **kwargs)
        except (asyncio.TimeoutError, ClientError, Error):
            raise Error(str(function))

    return wrapper


@attr.s
class LB2120:
    """Class for Netgear LB2120 interface."""

    hostname = attr.ib()
    websession = attr.ib()

    password = attr.ib(default=None)
    token = attr.ib(default=None)

    listeners = attr.ib(init=False, factory=list)
    max_sms_id = attr.ib(init=False, default=None)
    task = attr.ib(init=False, default=None)

    @property
    def _baseurl(self):
        return "http://{}/".format(self.hostname)

    def _url(self, path):
        """Build a complete URL for the device."""
        return self._baseurl + path

    async def add_sms_listener(self, listener):
        """Add a listener for new SMS."""
        self.listeners.append(listener)

    async def logout(self):
        """Cleanup resources."""
        self.websession = None
        self.token = None

    async def login(self, password=None):
        """Create a session with the modem."""
        if password is None:
            password = self.password
        else:
            self.password = password

        try:
            async with async_timeout.timeout(TIMEOUT):
                url = self._url('index.html')
                async with self.websession.get(url) as response:
                    text = await response.text()

                    match = re.search(r'name="token" value="(.*?)"', text)
                    if not match:
                        _LOGGER.error("No token found during login")
                        raise Error()

                    self.token = match.group(1)
                    _LOGGER.debug("Token: %s", self.token)

                url = self._url('Forms/config')
                data = {
                    'session.password': password,
                    'token': self.token
                }
                async with self.websession.post(url, data=data) as response:
                    _LOGGER.debug("Got cookie with status %d", response.status)

        except (asyncio.TimeoutError, ClientError, Error):
            raise Error("Could not login")

    @autologin
    async def sms(self, phone, message):
        """Send a message."""
        _LOGGER.debug("Send to %s via %s len=%d",
                      phone, self._baseurl, len(message))

        url = self._url('Forms/smsSendMsg')
        data = {
            'sms.sendMsg.receiver': phone,
            'sms.sendMsg.text': message,
            'sms.sendMsg.clientId': __name__,
            'action': 'send',
            'token': self.token
        }
        async with self.websession.post(url, data=data) as response:
            _LOGGER.debug("Sent message with status %d", response.status)

    @autologin
    async def delete_sms(self, sms_id):
        """Delete a message."""

        url = self._url('Forms/config')
        data = {
            'sms.deleteId': sms_id,
            'err_redirect': '/error.json',
            'ok_redirect': '/success.json',
            'token': self.token
        }
        async with self.websession.post(url, data=data) as response:
            _LOGGER.debug("Delete %d with status %d", sms_id, response.status)

    def _build_information(self, data):
        """Read the bits we need from returned data."""
        if 'wwan' not in data:
            raise Error()

        result = Information()

        result.usage = data['wwan']['dataUsage']['generic']['dataTransferred']
        result.upstream = data['failover']['backhaul']
        result.serial_number = data['general']['FSN']
        result.connection = data['wwan']['connection']
        result.connection_text = data['wwan']['connectionText']
        result.connection_type = data['wwan']['connectionType']
        result.current_nw_service_type = data['wwan']['currentNWserviceType']
        result.current_ps_service_type = data['wwan']['currentPSserviceType']
        result.register_network_display = data['wwan']['registerNetworkDisplay']
        result.roaming = data['wwan']['roaming']
        result.radio_quality = data['wwanadv']['radioQuality']
        result.rx_level = data['wwanadv']['rxLevel']
        result.tx_level = data['wwanadv']['txLevel']
        result.current_band = data['wwanadv']['curBand']
        result.cell_id = data['wwanadv']['cellId']

        for msg in [m for m in data['sms']['msgs'] if 'text' in m]:
            # {'id': '6', 'rxTime': '11/03/18 08:18:11 PM', 'text': 'tak tik',
            #  'sender': '555-987-654', 'read': False}
            dt = datetime.strptime(msg['rxTime'], '%d/%m/%y %I:%M:%S %p')
            element = SMS(int(msg['id']), dt, not msg['read'], msg['sender'], msg['text'])
            result.sms.append(element)
        result.sms.sort(key=lambda sms: sms.id)

        return result

    @autologin
    async def information(self):
        """Return the current information."""
        url = self._url('model.json')
        async with self.websession.get(url) as response:
            data = json.loads(await response.text())

            result = self._build_information(data)

            self._sms_events(result)

            return result

    def _sms_events(self, information):
        """Send events for each new SMS."""
        if not self.listeners:
            return

        if self.max_sms_id is not None:
            new_sms = (s for s in information.sms if s.id > self.max_sms_id)
            for sms in new_sms:
                for listener in self.listeners:
                    listener(sms)

        if information.sms:
            self.max_sms_id = max(s.id for s in information.sms)


class Modem(LB2120):
    """Class for any modem."""
