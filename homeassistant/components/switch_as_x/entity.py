"""Base entity for the Switch as X integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity, ToggleEntity
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN as SWITCH_AS_X_DOMAIN


class BaseEntity(Entity):
    """Represents a Switch as an X."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_title: str,
        switch_entity_id: str,
        unique_id: str | None,
    ) -> None:
        """Initialize Switch as an X."""
        registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        wrapped_switch = registry.async_get(switch_entity_id)
        device_id = wrapped_switch.device_id if wrapped_switch else None
        entity_category = wrapped_switch.entity_category if wrapped_switch else None
        has_entity_name = wrapped_switch.has_entity_name if wrapped_switch else False

        name: str | None = config_entry_title
        if wrapped_switch:
            name = wrapped_switch.name or wrapped_switch.original_name

        self._device_id = device_id
        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )
        self._attr_entity_category = entity_category
        self._attr_has_entity_name = has_entity_name
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._switch_entity_id = switch_entity_id

    @callback
    def async_state_changed_listener(self, event: Event | None = None) -> None:
        """Handle child updates."""
        if (
            state := self.hass.states.get(self._switch_entity_id)
        ) is None or state.state == STATE_UNAVAILABLE:
            self._attr_available = False
            return

        self._attr_available = True

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        @callback
        def _async_state_changed_listener(event: Event | None = None) -> None:
            """Handle child updates."""
            self.async_state_changed_listener(event)
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._switch_entity_id], _async_state_changed_listener
            )
        )

        # Call once on adding
        _async_state_changed_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                SWITCH_AS_X_DOMAIN,
                {"entity_id": self._switch_entity_id},
            )


class BaseToggleEntity(BaseEntity, ToggleEntity):
    """Represents a Switch as a ToggleEntity."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Forward the turn_on command to the switch in this light switch."""
        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._switch_entity_id},
            blocking=True,
            context=self._context,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Forward the turn_off command to the switch in this light switch."""
        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._switch_entity_id},
            blocking=True,
            context=self._context,
        )

    @callback
    def async_state_changed_listener(self, event: Event | None = None) -> None:
        """Handle child updates."""
        super().async_state_changed_listener(event)
        if (
            not self.available
            or (state := self.hass.states.get(self._switch_entity_id)) is None
        ):
            return

        self._attr_is_on = state.state == STATE_ON
