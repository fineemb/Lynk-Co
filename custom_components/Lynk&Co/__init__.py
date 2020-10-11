"""
Component to integrate with xiaomi cloud.

For more details about this component, please refer to
https://github.com/fineemb/xiaomi-cloud
"""
import asyncio
import json
import datetime
import time
import logging
import re
import base64
import hashlib

import async_timeout
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from urllib import parse
from aiohttp.client_exceptions import ClientConnectorError
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.device_tracker import (
    ATTR_BATTERY,
    DOMAIN as DEVICE_TRACKER,
)
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
    ATTR_ENTITY_ID
)

from .const import (
    DOMAIN,
    UNDO_UPDATE_LISTENER,
    COORDINATOR,
    LYNKCO_COMPONENT
)

SET_SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id
})
SERVICE_SCHEMA_ULOCK = SET_SERVICE_SCHEMA.extend({
    vol.Required("value"):
        vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3))
})
SERVICE_SCHEMA_HLF = SET_SERVICE_SCHEMA.extend({
    vol.Required("value"):
        vol.All(vol.Coerce(str), vol.Clamp('horn-light-flash', 'light-flash', 'horn-flash'))
})
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured LynkCo."""
    hass.data[DOMAIN] = {"devices": set(), "unsub_device_tracker": {}}
    return True

async def async_setup_entry(hass, config_entry) -> bool:
    """Set up LynkCo as config entry."""
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, 5)

    _LOGGER.debug("Username: %s", username)


    coordinator = LynkCoDataUpdateCoordinator(
        hass, username, password, scan_interval
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    undo_listener = config_entry.add_update_listener(update_listener)

    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENER: undo_listener,
    }
    for component in LYNKCO_COMPONENT:
        _LOGGER.debug("Loading %s", component)
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    async def services(call):
        """Handle the service call."""
        
        service = call.service
        vin = call.data.get("entity_id")

        data = {'service':service,
                'entity_id':vin,
                }
        if service == "unlock":
            data['value'] = call.data.get("value")
        elif service == "hlf":
            data['value'] = call.data.get("value")

        await coordinator._send_command(data)

    hass.services.async_register(DOMAIN, "start", services, schema=SET_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "stop", services, schema=SET_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "unlock", services, schema=SERVICE_SCHEMA_ULOCK)
    hass.services.async_register(DOMAIN, "lock", services, schema=SET_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "hlf", services, schema=SERVICE_SCHEMA_HLF)

    return True


async def async_unload_entry(hass, config_entry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in LYNKCO_COMPONENT
            ]
        )
    )
    hass.data[DOMAIN][config_entry.entry_id][UNDO_UPDATE_LISTENER]()

    username = config_entry.title
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.debug("Unloaded entry for %s", username)
        return True
    return False

async def update_listener(hass, config_entry):
    """Update when config_entry options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)

class LynkCoDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching XiaomiCloud data API."""
    def __init__(self, hass, user, password, scan_interval):
        """Initialize."""
        self._username = user
        self._password = password
        self._cookies = {}
        self._accessToken = None
        self._userId = None
        self._refreshToken = None
        self._vehicles = None
        self._vehicles_status = [ ]
        self._scan_interval = scan_interval
        self.login_result = False
        self.service_data = {}
        self.service = None

        update_interval = (
            datetime.timedelta(seconds=self._scan_interval)
        )
        _LOGGER.debug("Data will be update every %s", update_interval)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _send_command(self, data):
        self.service_data = data
        self.service = True
        await self.async_refresh()

    async def _send_RES_command(self, session):
        flag = True
        vin = self.hass.states.get(self.service_data['entity_id']).attributes['vin']
        # session.cookie_jar.clear()
        url = 'http://api.xchanger.cn/geelyTCAccess/tcservices/vehicle/telematics/{}'.format(vin)
        headers ={
                    "authorization" : self._accessToken,
                    "X-APP-ID" : "xiaokanl",
                    "X-OPERATOR-CODE":"LYNKCO",
                    "Content-Type":"application/json",
                    "Accept":"application/json;responseformat=3"
                }
        data = {"command":"",
                "creator":"tc",
                "serviceId":"",
                "timestamp":int(time.time()),
                "userId":self._userId
                }
        if self.service_data['service'] == 'start':
            data['command'] = 'start'
            data['serviceId'] = 'RES'
        elif self.service_data['service'] == 'stop':
            data['command'] = 'stop'
            data['serviceId'] = 'RES'
        elif self.service_data['service'] == 'lock':    
            data['command'] = 'start'
            data['serviceId'] = 'RDL'
        elif self.service_data['service'] == 'unlock':    
            data['command'] = 'start'
            data['serviceId'] = 'RDU'
            data['serviceParameters'] = [{
                                        "key":"time.window",
                                        "value":self.service_data['value']  
                                        }]
        elif self.service_data['service'] == 'hlf':    
            data['command'] = 'start'
            data['serviceId'] = 'RHL'
            data['serviceParameters'] = [{
                                        "key":"rhl",
                                        "value":self.service_data['value']  
                                        }]

        _LOGGER.debug("_send_RES_command request: \nurl: %s\nheaders: %s\ndata: %s", url,headers,data)
        r = await session.put(url,data=json.dumps(data), headers=headers )
        _LOGGER.debug("_send_RES_command response: \nstatus: %s\nurl: %s\nheaders: %s\ncontent: %s", r.status,r.url,r.headers,await r.text('UTF-8'))
        if r.status == 200:
            # _LOGGER.debug("_send_RES_command_status: %s", json.loads(await r.text()))
            _LOGGER.error("message: %s", json.loads(await r.text())['message'])
            flag = True
            self.login_result = True
            self.service = False
            self.service_data = None
            return flag

        flag = False
        self.login_result = False
        self.service = False
        self.service_data = None
        return flag

    async def _login_lynkco(self, session):
        url = 'https://api.xchanger.cn/api/v1/user/login'
        headers = {
            'Accept':'application/json;charset=UTF-8',
            'X-APP-ID':'xiaokanl',
            'Content-Type':'application/x-www-form-urlencoded'
        }
        auth_post_data = {
                          'password': hashlib.md5(self._password.encode('utf-8')).hexdigest().lower(),
                          'username': self._username}
        try:
            r = await session.post(url, headers=headers, data=auth_post_data)
            if r.status == 200:
                data = json.loads((await r.text()))
                _LOGGER.debug("_login_lynkco_res: %s", data)
                if data['resultMessage'] == 'Success':
                    self._accessToken = data['accessToken']
                    self._userId = data['userId']
                    self._refreshToken = data['refreshToken']
                    self.login_result = True
                    return True
                else:
                    return False
            else:
                return False
        except BaseException as e:
            _LOGGER.warning(e.args[0])
            return False

    async def _get_vehicles(self, session):
        url = 'https://api.xchanger.cn/device_platform/user/vehicle?id={}'.format(self._userId)
        headers = {
            'Accept':'application/json;charset=UTF-8',
            'X-APP-ID':'xiaokanl',
            'x-operator-code':'LYNKCO',
            'authorization':self._accessToken
        }
        try:
            r = await session.get(url, headers=headers)
            if r.status == 200:
                data = json.loads(await r.text())
                self._vehicles = data['list']
                # _LOGGER.debug("_get_vehicles: %s", self._vehicles)
                return True
            else:
                return False
        except BaseException as e:
            _LOGGER.warning(e.args[0])
            return False

    async def _get_vehicle_status(self, session):
        headers = {
            'Accept':'application/json;charset=UTF-8',
            'x-operator-code':'LYNKCO',
            'authorization':self._accessToken
        }
        redata = []
        for item in self._vehicles:
            url = "http://api.xchanger.cn/geelyTCAccess/tcservices/vehicle/status/{}?userId={}&latest=false&target=more%2Cbasic".format(
                item['vin'], 
                self._userId)
            # _LOGGER.debug("_get_vehicle_status_url:%s \n %s",self._accessToken, url)
            try:
                r = await session.get(url, headers=headers)
                # _LOGGER.debug("_get_vehicle_status response: \nstatus: %s\nurl: %s\nheaders: %s\ncontent: %s", r.status,r.url,r.headers,await r.text('UTF-8'))
                if r.status == 200:
                    data = json.loads(await r.text())['data']
                    data['plateNo']=item['plateNo'] 
                    data['seriesName']=item['seriesName']
                    data['colorCode']=item['colorCode']
                    data['tboxPlatform']=item['tboxPlatform']
                    # _LOGGER.debug("_get_vehicle_status: %s", data)
                    redata.append(data)
                else:
                    self.login_result = False
                    return False
            except BaseException as e:
                _LOGGER.debug(e.args[0])
                return False
        return redata

    @asyncio.coroutine
    async def _async_update_data(self):
        """Update data via library."""
        try:
            session = async_get_clientsession(self.hass)
            session.cookie_jar.clear()
            if self.login_result is True:
                # _LOGGER.debug('login_result: %s',self.login_result)
                if self.service:
                    tmp = await self._send_RES_command(session)
                tmp = await self._get_vehicle_status(session)
            else:
                tmp = await self._login_lynkco(session)
                if not tmp:
                    _LOGGER.debug('Login failed')
                else:
                    tmp = await self._get_vehicles(session)
                    _LOGGER.debug('_get_vehicles: %s',tmp)
                    if not tmp:
                        _LOGGER.debug('Get vehicles failed')
                    else:
                        if self.service:
                            tmp = await self._send_RES_command(session)
                        tmp = await self._get_vehicle_status(session)
                        if not tmp:
                            _LOGGER.debug('Get status failed')

        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        # _LOGGER.debug("Data Coordinator: %s", tmp)
        return tmp
