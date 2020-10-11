
"""Adds config flow for Colorfulclouds."""
import logging
import json
import hashlib
import voluptuous as vol
from urllib import parse
from collections import OrderedDict
from homeassistant.helpers import aiohttp_client, config_validation as cv
from homeassistant.const import CONF_NAME

from homeassistant import config_entries, core, exceptions
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import callback
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)

from .const import (
    DOMAIN
)



_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class LynkcolowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return LynkcoOptionsFlow(config_entry)

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._user = None
        self._password = None
        self._headers = {}

    async def async_step_user(self, user_input={}):
        self._errors = {}
        if user_input is not None:
            # Check if entered host is already in HomeAssistant
            existing = await self._check_existing(user_input[CONF_USERNAME])
            if existing:
                return self.async_abort(reason="already_configured")

            # If it is not, continue with communication test
            self._user = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            session = async_get_clientsession(self.hass)  
            try:
                session.cookie_jar.clear()
                tmp = await self._login_lynkco(session)
                if not tmp:
                    _LOGGER.warning("login lynkco Failed")
                    self._errors["base"] = "login_url_failed"
                    return await self._show_config_form(user_input)
                else:
                    return self.async_create_entry(
                        title=user_input[CONF_USERNAME], data=user_input
                    )
                return True
            except BaseException as e:
                _LOGGER.warning(e.args[0])
                return False
            return await self._show_config_form(user_input)
        return await self._show_config_form(user_input)
    async def _login_lynkco(self, session):
        url = 'https://api.xchanger.cn/api/v1/user/login'
        self._headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self._headers['Accept'] = 'application/json;charset=UTF-8'
        self._headers['X-APP-ID'] = 'xiaokanl'
        auth_post_data = {
                          'password': hashlib.md5(self._password.encode('utf-8')).hexdigest().lower(),
                          'username': self._user}
        try:
            r = await session.post(url, headers=self._headers, data=auth_post_data)
            if r.status == 200:
                data = json.loads((await r.text()))
                _LOGGER.debug("_login_lynkco_res: %s", data)
                if data['resultMessage'] == 'Success':
                    self._accessToken = data['accessToken']
                    self._userId = data['userId']
                    self._refreshToken = data['refreshToken']
                    return True
        except BaseException as e:
            _LOGGER.warning(e.args[0])
            return False

    async def _show_config_form(self, user_input):
        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_USERNAME)] = str
        data_schema[vol.Required(CONF_PASSWORD)] = str
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def async_step_import(self, user_input):
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

    async def _check_existing(self, host):
        for entry in self._async_current_entries():
            if host == entry.data.get(CONF_NAME):
                return True

class LynkcoOptionsFlow(config_entries.OptionsFlow):
    """Config flow options for Colorfulclouds."""

    def __init__(self, config_entry):
        """Initialize Colorfulclouds options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(CONF_SCAN_INTERVAL, 5),
                    ):int
                }
            ),
        )

