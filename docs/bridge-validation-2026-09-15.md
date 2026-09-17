# Shadow bridge validation — September 15, 2026

This change adds a fourth package, `truck_bridge`, after the previously published interface commit `9b06bf6`.
It retains the five supplied files byte-for-byte and does not include perception runtime source or model weights.

| Check | Humble | Jazzy |
|---|---|---|
| Four-package build on arm64 Linux | Passed | Passed |
| Bridge policy + actual ROS pub/sub tests | 27 passed, zero skipped | 27 passed, zero skipped |
| Separate private output-owner integration via actual DDS | 1 passed, zero skipped | 1 passed, zero skipped |

The bridge tests cover steering sign, independent validity flags, numeric limits, no-lane and zero-speed decisions,
receipt expiry, competing publishers, graph-observed publisher replacement, remapping, immediate stop delivery to
the optional decision sink, and propagation of sink failures. Both distro tests ran against the final callback API.

The private controller integration used the production output owner and speed-control boundary with a fake
flight-controller sender that raises on every send. No sends occurred. It checked steering signs, handback, valid
steering with zero/missing speed, no-lane, timeout, publisher replacement, manual controls and runtime output guards.
That factory/test lives in the separate truck research repository; it is not part of this public package.

## Limits

- No phone, model inference, flight controller or truck was used by these bridge tests.
- The shared message has no acquisition timestamp/sequence. Fresh receipt does not prove a fresh source image.
- Publisher IDs come from ROS graph snapshots. They do not authenticate individual queued commands.
- The executable has no vehicle writer or output-enable option. An external decision sink requires its own guarded
  integration; this package does not turn arbitrary callbacks into safe actuator owners.
- Human vetoes, plant calibration, physical steering direction, stop distance and rearming need intended-host and
  controlled hardware acceptance before driving.

CI builds all four packages on Humble and Jazzy and requires nonempty bridge results with no skipped bridge tests.
Local container results are not a claim that a new branch has run successfully on hosted CI.
