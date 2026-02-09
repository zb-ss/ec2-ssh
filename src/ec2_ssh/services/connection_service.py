"""Connection service for profile resolution and proxy configuration."""

from __future__ import annotations
import logging
from typing import Optional, Dict

from ec2_ssh.services.interfaces import ConnectionServiceInterface
from ec2_ssh.config.manager import ConfigManager
from ec2_ssh.config.schema import ConnectionProfile
from ec2_ssh.utils.match_utils import matches_conditions

logger = logging.getLogger(__name__)


class ConnectionService(ConnectionServiceInterface):
    """Connection service for resolving connection profiles and bastion configuration.

    Implements match condition evaluation with AND logic for all conditions.
    """

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize connection service.

        Args:
            config_manager: Configuration manager instance.
        """
        self._config_manager = config_manager

    def resolve_profile(self, instance: dict) -> Optional[ConnectionProfile]:
        """Find the first matching connection profile for an instance.

        Evaluates connection rules in order. Returns the first profile
        whose match conditions are satisfied.

        Args:
            instance: Instance dictionary.

        Returns:
            Matching ConnectionProfile, or None if no rules match (direct connection).
        """
        config = self._config_manager.get()
        for rule in config.connection_rules:
            if matches_conditions(instance, rule.match_conditions):
                # Find the profile by name
                for profile in config.connection_profiles:
                    if profile.name == rule.profile_name:
                        logger.info(
                            "Instance %s matched rule '%s', using profile '%s'",
                            instance.get('id'),
                            rule.name,
                            profile.name
                        )
                        return profile
                logger.warning(
                    "Connection rule '%s' references missing profile '%s'",
                    rule.name,
                    rule.profile_name
                )
        logger.debug(
            "No connection rules matched for instance %s, using direct connection",
            instance.get('id')
        )
        return None

    def get_proxy_jump_string(
        self,
        profile: ConnectionProfile,
        key_path: Optional[str] = None
    ) -> Optional[str]:
        """Build ProxyJump string from profile. Returns None if no bastion configured.

        Format: [user@]host[:port]
        If profile has proxy_command instead, return None (handled separately).

        Args:
            profile: Connection profile with bastion config.
            key_path: SSH key path for bastion (optional, not used in ProxyJump string).

        Returns:
            ProxyJump string (user@host or user@host:port), or None if no bastion.
        """
        if not profile.bastion_host:
            return None

        parts = []
        if profile.bastion_user:
            parts.append(f"{profile.bastion_user}@")
        parts.append(profile.bastion_host)
        if profile.ssh_port != 22:
            parts.append(f":{profile.ssh_port}")

        proxy_jump = ''.join(parts)
        logger.debug("Built ProxyJump string: %s", proxy_jump)
        return proxy_jump

    def get_target_host(
        self,
        instance: dict,
        profile: Optional[ConnectionProfile] = None
    ) -> str:
        """Get the target host for connection.

        If through bastion, use private IP. Direct connection uses public IP.

        Args:
            instance: Instance dictionary.
            profile: Connection profile (uses bastion_host to determine routing).

        Returns:
            IP address or hostname to connect to.
        """
        if profile and profile.bastion_host:
            # Connection through bastion - use private IP
            host = instance.get('private_ip') or instance.get('public_ip', '')
            logger.debug(
                "Using private IP for bastion connection: %s",
                host
            )
        else:
            # Direct connection - use public IP
            host = instance.get('public_ip', '')
            logger.debug(
                "Using public IP for direct connection: %s",
                host
            )
        return host
