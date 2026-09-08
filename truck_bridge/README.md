# truck_bridge

Subscribes `/desired_control`, publishes to the Pixhawk. First implementation: MAVLink `RC_CHANNELS_OVERRIDE` on channel 1
while the vehicle is in MANUAL (the path the truck drives on today); MAVROS `GUIDED` later once the compass and a yaw source exist.
Negates curvature once (wire: + = left; truck: + = right). Holds the last valid angle and requests speed 0 when
`listen_to_steering` is false. Not yet written.
