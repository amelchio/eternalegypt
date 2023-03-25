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
    serial_number = attr.ib(default=None)
    usage = attr.ib(default=None)
    upstream = attr.ib(default=None)
    wire_connected = attr.ib(default=None)
    mobile_connected = attr.ib(default=None)
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
    sms = attr.ib(factory=list)
    items = attr.ib(factory=dict)


def autologin(function, timeout=TIMEOUT):
    """Decorator that will try to login and redo an action before failing."""
    @wraps(function)
    async def wrapper(self, *args, **kwargs):
        """Wrap a function with timeout."""
        if self.websession is None:
            _LOGGER.debug("Already logged out")
            return

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
        # Work around missing https://github.com/aio-libs/aiohttp/pull/3576
        try:
            await self._login(password)
        except (asyncio.TimeoutError, ClientError, Error):
            await self._login(password)

    async def _login(self, password=None):
        """Create a session with the modem."""
        if password is None:
            password = self.password
        else:
            self.password = password

        try:
            async with async_timeout.timeout(TIMEOUT):
                url = self._url('model.json')
                async with self.websession.get(url) as response:
                    data = json.loads(await response.text())
                    self.token = data.get('session', {}).get('secToken')

                    if self.token is None:
                        _LOGGER.error("No token found during login")
                        raise Error()

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

    def _config_call(self, key, value):
        """Set a configuration key to a certain value."""
        url = self._url('Forms/config')
        data = {
            key: value,
            'err_redirect': '/error.json',
            'ok_redirect': '/success.json',
            'token': self.token
        }
        return self.websession.post(url, data=data)

    @autologin
    async def disconnect_lte(self):
        """Do an LTE disconnect."""
        async with self._config_call('wwan.connect', 'Disconnect') as response:
            _LOGGER.debug("Disconnected LTE with status %d", response.status)

    @autologin
    async def connect_lte(self):
        """Do an LTE reconnect."""
        async with self._config_call('wwan.connect', 'DefaultProfile') as response:
            _LOGGER.debug("Connected to LTE with status %d", response.status)

    @autologin
    async def delete_sms(self, sms_id):
        """Delete a message."""
        async with self._config_call('sms.deleteId', sms_id) as response:
            _LOGGER.debug("Delete %d with status %d", sms_id, response.status)

    @autologin
    async def set_failover_mode(self, mode):
        """Set failover mode."""
        modes = {
            'auto': 'Auto',
            'wire': 'WAN',
            'mobile': 'LTE',
        }

        if mode not in modes.keys():
            _LOGGER.error("Invalid mode %s not %s", mode, "/".join(modes.keys()))
            return

        async with self._config_call('failover.mode', modes[mode]) as response:
            _LOGGER.debug("Set mode to %s", mode)

    @autologin
    async def set_autoconnect_mode(self, mode):
        """Set autoconnect mode."""
        modes = {
            'never': 'Never',
            'home': 'HomeNetwork',
            'always': 'Always',
        }

        if mode not in modes.keys():
            _LOGGER.error("Invalid mode %s not %s", mode, "/".join(modes.keys()))
            return

        async with self._config_call('wwan.autoconnect', modes[mode]) as response:
            _LOGGER.debug("Set mode to %s", mode)

    @autologin
    async def router_restart(self):
        """Do a device restart."""
        async with self._config_call('general.shutdown', 'restart') as response:
            _LOGGER.debug("Router restart %d", response.status)

    @autologin
    async def factory_reset(self):
        """Do a factory reset."""
        async with self._config_call('general.factoryReset', 1) as response:
            _LOGGER.debug("Factory reset %d", response.status)


    def _build_information(self, data):
        """Read the bits we need from returned data."""
        result = Information()

        result.serial_number = data['general']['FSN']
        result.usage = data['wwan']['dataUsage']['generic']['dataTransferred']
        if 'failover' in data:
            result.upstream = data['failover'].get('backhaul')
            result.wire_connected = data['failover'].get('wanConnected')
        result.mobile_connected = (data['wwan']['connection'] == 'Connected')
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

        mdy_models = ('MR1100')

        for msg in [m for m in data['sms']['msgs'] if 'text' in m]:
            # {'id': '6', 'rxTime': '11/03/18 08:18:11 PM', 'text': 'tak tik',
            #  'sender': '555-987-654', 'read': False}
            try:
                if ('model' in data['general'] and data['general']['model'] in mdy_models):
                    dt = datetime.strptime(msg['rxTime'], '%m/%d/%y %I:%M:%S %p')
                else:
                    dt = datetime.strptime(msg['rxTime'], '%d/%m/%y %I:%M:%S %p')
            except ValueError:
                dt = None

            element = SMS(int(msg['id']), dt, not msg['read'], msg['sender'], msg['text'])
            result.sms.append(element)
        result.sms.sort(key=lambda sms: sms.id)

        result.items = {
            key: value
            for key, value in flatten(data).items()
            if key not in ('webd.adminpassword', 'session.sectoken', 'wifi.guest.passphrase', 'wifi.passphrase')
        }

        return result

    @autologin
    async def information(self):
        """Return the current information."""
        url = self._url('model.json')
        async with self.websession.get(url) as response:
            data = json.loads(await response.text())

            try:
                result = self._build_information(data)
                _LOGGER.debug("Did read information: %s", data)
            except KeyError as ex:
                _LOGGER.debug("Failed to read information (%s): %s", ex, data)
                raise Error()

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

def flatten(obj, path=""):
    """Flatten nested dicts into hierarchical keys."""
    result = {}
    if isinstance(obj, dict):
        for key, item in obj.items():
            result.update(flatten(item, path=(path + "." if path else "") + key.lower()))
    elif isinstance(obj, (str, int, float, bool)):
        result[path] = obj
    return result
