# Supplied source and repository scaffolding

The collaborator supplied the message package and two example implementation files on 2026-09-10. The local staging
copy used for this delivery was made on 2026-09-13. Publication scope is recorded in the
[resolved decision](DECISION-2026-09-13-what-goes-public.md).

| Supplied path | Repository path |
|---|---|
| `control_interfaces/msg/ControlMsg.msg` | Same |
| `control_interfaces/CMakeLists.txt` | Same |
| `control_interfaces/package.xml` | Same |
| `control_node_pkg/src/control_publisher_node.cpp` | `examples/control_node_pkg/src/control_publisher_node.cpp` |
| `control_listener_pkg/src/control_listener_node.cpp` | `examples/control_listener_pkg/src/control_listener_node.cpp` |

All five files are preserved byte for byte, including existing metadata and line endings. The message package's
maintainer and license fields remain the supplied placeholders; they have not been rewritten as though they were
upstream declarations. The repository's own additions use its MIT license.

The supplied examples contain class implementations but did not include their referenced headers, executable entry
points, package/build files or a scheduler for `publish_message()`. This repository adds those missing pieces around
the original `.cpp` files. The publisher wrapper invokes the supplied method every 100 ms; its sample values remain
unchanged. The wrappers and tests are repository-authored, not attributed to the collaborator.

[The SHA-256 manifest](supplied-source-sha256.json) records the initial copies. Check it without installing ROS:

```bash
python3 tools/check_interface.py
```

Where the original private staging directory is available, also compare directly:

```bash
python3 tools/check_interface.py --staged-source .staging-model-side
```

CI runs the first check before building. An intentional update to supplied code should replace it from an authorized
upstream delivery and update the manifest and this provenance record together. The checksum check protects these
copies against accidental editing; it is not a cryptographic signature from the collaborator.

Only the five listed supplied files are included. The perception runtime and model weights are excluded.
