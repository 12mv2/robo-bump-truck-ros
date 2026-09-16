"""Pure command policy. Receipt freshness is not source-image freshness."""

from dataclasses import dataclass
import math
from typing import Optional


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class Decision:
    received_at: Optional[float]
    steer: Optional[float]
    speed_mps: Optional[float]
    stop_reason: Optional[str]
    manual_steering: bool
    source_age_verified: bool = False


class BridgePolicy:
    """Convert one fresh command into requests, without actuator authority.

    Defaults are proposed smoke-test limits, not a validated vehicle profile.
    Invalid flagged-off values are reference data and are never interpreted.
    """

    def __init__(self, *, full_lock_curvature=1.0 / 0.70,
                 max_curvature=1.0 / 0.70, max_speed=0.5, timeout=0.5):
        values = (full_lock_curvature, max_curvature, max_speed, timeout)
        if any(not finite_number(value) or value <= 0 for value in values):
            raise ValueError('limits and timeout must be finite positive numbers')
        if max_curvature > full_lock_curvature:
            raise ValueError('max_curvature cannot exceed full_lock_curvature')
        self.full_lock_curvature = float(full_lock_curvature)
        self.max_curvature = float(max_curvature)
        self.max_speed = float(max_speed)
        self.timeout = float(timeout)
        self._last_clock = None
        self._decision = Decision(None, None, None, 'startup', True)

    def clear(self, reason, received_at=None):
        """Withdraw requests; never imply a physical stop or refresh a lease."""
        self._decision = Decision(received_at, None, None, str(reason), True)
        return self._decision

    def _clock_ok(self, value):
        if not finite_number(value) or value < 0:
            self.clear('clock_invalid')
            return False
        if self._last_clock is not None and value < self._last_clock:
            self.clear('clock_regressed')
            return False
        self._last_clock = value
        return True

    def accept(self, message, received_at):
        """Accept a new message at its local monotonic receipt time."""
        if not self._clock_ok(received_at):
            return self._decision
        try:
            steering_valid = message.listen_to_steering
            speed_valid = message.listen_to_speed
            if not isinstance(steering_valid, bool) or not isinstance(speed_valid, bool):
                return self.clear('invalid_flags', received_at)
            steer = speed = None
            if steering_valid:
                curvature = message.desired_curvature
                if not finite_number(curvature):
                    return self.clear('curvature_nonfinite', received_at)
                if abs(curvature) > self.max_curvature:
                    return self.clear('curvature_out_of_range', received_at)
                # Wire left-positive -> truck right-positive exactly once.
                steer = -float(curvature) / self.full_lock_curvature
            if speed_valid:
                speed = message.desired_speed
                if not finite_number(speed):
                    return self.clear('speed_nonfinite', received_at)
                if not 0 <= speed <= self.max_speed:
                    return self.clear('speed_out_of_range', received_at)
                speed = float(speed)
        except AttributeError:
            return self.clear('malformed_command', received_at)

        reason = None
        if not speed_valid:
            reason = 'no_speed_authority'
        elif speed == 0:
            reason = 'zero_speed'
        elif not steering_valid:
            speed = 0.0
            reason = 'no_steering_authority'
        self._decision = Decision(received_at, steer, speed, reason, not steering_valid)
        return self._decision

    def snapshot(self, now):
        """Read the current decision without renewing its receipt timestamp."""
        if not self._clock_ok(now):
            return self._decision
        received_at = self._decision.received_at
        if received_at is not None and now - received_at >= self.timeout:
            return self.clear('command_timeout', received_at)
        return self._decision
