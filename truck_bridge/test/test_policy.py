from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from truck_bridge.policy import BridgePolicy


def command(curvature=0.5, speed=0.3, steer=True, throttle=True):
    return SimpleNamespace(desired_curvature=curvature, desired_speed=speed,
                           listen_to_steering=steer, listen_to_speed=throttle)


@pytest.mark.parametrize('wire,expected', [(0.5, -0.25), (-0.5, 0.25), (0, 0)])
def test_curvature_sign_and_empirical_scale(wire, expected):
    policy = BridgePolicy(full_lock_curvature=2, max_curvature=1)
    result = policy.accept(command(curvature=wire), 10)
    assert result.steer == expected
    assert result.speed_mps == 0.3
    assert result.stop_reason is None
    assert not result.manual_steering
    assert not result.source_age_verified
    with pytest.raises(FrozenInstanceError):
        result.steer = 1


@pytest.mark.parametrize('steer,speed_valid,speed,expected_steer,expected_speed,reason', [
    (True, True, 0.0, -0.35, 0.0, 'zero_speed'),
    (False, True, 0.0, None, 0.0, 'zero_speed'),
    (False, True, 0.3, None, 0.0, 'no_steering_authority'),
    (True, False, 0.3, -0.35, None, 'no_speed_authority'),
    (False, False, 0.3, None, None, 'no_speed_authority'),
])
def test_validity_combinations_and_zero_stop(steer, speed_valid, speed,
                                          expected_steer, expected_speed, reason):
    result = BridgePolicy().accept(command(speed=speed, steer=steer, throttle=speed_valid), 1)
    if expected_steer is None:
        assert result.steer is None
    else:
        assert result.steer == pytest.approx(expected_steer)
    assert result.speed_mps == expected_speed
    assert result.stop_reason == reason
    assert result.manual_steering is (not steer)


def test_reference_only_fields_are_not_interpreted_or_reused():
    policy = BridgePolicy()
    policy.accept(command(), 1)
    result = policy.accept(command(curvature=float('nan'), speed=float('inf'),
                                   steer=False, throttle=False), 1.1)
    assert result.steer is None and result.speed_mps is None
    assert result.manual_steering
    result = policy.accept(command(curvature=float('nan'), speed=0, steer=False), 1.2)
    assert result.stop_reason == 'zero_speed'
    assert result.speed_mps == 0


@pytest.mark.parametrize('field,value,reason', [
    ('desired_curvature', float('nan'), 'curvature_nonfinite'),
    ('desired_curvature', float('inf'), 'curvature_nonfinite'),
    ('desired_curvature', -2, 'curvature_out_of_range'),
    ('desired_curvature', True, 'curvature_nonfinite'),
    ('desired_speed', float('nan'), 'speed_nonfinite'),
    ('desired_speed', float('-inf'), 'speed_nonfinite'),
    ('desired_speed', -0.01, 'speed_out_of_range'),
    ('desired_speed', 0.51, 'speed_out_of_range'),
    ('listen_to_speed', 1, 'invalid_flags'),
])
def test_fault_withdraws_previous_requests(field, value, reason):
    policy = BridgePolicy()
    policy.accept(command(), 1)
    message = command()
    setattr(message, field, value)
    result = policy.accept(message, 1.1)
    assert result.stop_reason == reason
    assert result.steer is None and result.speed_mps is None
    assert result.manual_steering


def test_expiry_never_renews_receipt_and_new_message_is_only_diagnostic_recovery():
    policy = BridgePolicy(timeout=0.5)
    assert policy.snapshot(1).stop_reason == 'startup'
    policy.accept(command(), 2)
    for now in (2.1, 2.2, 2.49):
        result = policy.snapshot(now)
        assert result.received_at == 2 and result.stop_reason is None
    expired = policy.snapshot(2.5)
    assert expired.stop_reason == 'command_timeout'
    assert expired.received_at == 2
    assert expired.steer is None and expired.speed_mps is None
    assert policy.snapshot(3).stop_reason == 'command_timeout'
    recovered = policy.accept(command(), 3.1)
    assert recovered.received_at == 3.1
    assert not recovered.source_age_verified


def test_regressing_or_invalid_clock_withdraws_and_does_not_backdate_a_command():
    policy = BridgePolicy()
    policy.accept(command(), 2)
    assert policy.snapshot(1.9).stop_reason == 'clock_regressed'
    assert policy.accept(command(), 1.8).stop_reason == 'clock_regressed'
    assert policy.accept(command(), float('nan')).stop_reason == 'clock_invalid'
    assert policy.snapshot(2.1).steer is None
    assert policy.accept(command(), 2.2).stop_reason is None


def test_limits_exactly_accepted_and_malformed_message_clears():
    policy = BridgePolicy(full_lock_curvature=1, max_curvature=1, max_speed=0.5)
    result = policy.accept(command(curvature=-1, speed=0.5), 1)
    assert result.steer == 1 and result.speed_mps == 0.5
    result = policy.accept(SimpleNamespace(), 2)
    assert result.stop_reason == 'malformed_command' and result.steer is None


@pytest.mark.parametrize('kwargs', [
    {'timeout': 0}, {'timeout': float('nan')}, {'max_speed': -1},
    {'full_lock_curvature': True}, {'max_curvature': 2, 'full_lock_curvature': 1},
])
def test_bad_configuration_refused(kwargs):
    with pytest.raises(ValueError):
        BridgePolicy(**kwargs)
