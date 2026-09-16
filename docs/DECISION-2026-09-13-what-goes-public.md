# Publication scope — resolved 2026-09-15

The earlier version of this decision left publication permission open. The supplied correspondence resolves it:
on 2026-09-10 Colin asked for the message package and publish/listen examples for verbatim inclusion in this public
interface repository, and the collaborator supplied those files for that purpose that evening.
No new permission request is needed for this scope.

## Authorized supplied files

- `control_interfaces/msg/ControlMsg.msg`
- `control_interfaces/CMakeLists.txt`
- `control_interfaces/package.xml`
- `control_node_pkg/src/control_publisher_node.cpp`
- `control_listener_pkg/src/control_listener_node.cpp`

The message package is copied unchanged to the repository root. The two unchanged example source files are under
`examples/`, with repository-authored headers, entry points, package/build files and a publisher timer to make them
runnable. [Provenance and integrity checks](source-provenance.md) distinguish those additions from supplied code.

## Excluded

The collaborator's perception runtime and model weights are outside the publication scope. The private local staging
directory remains ignored. Build, install and log outputs also remain ignored. This scope does not imply permission to
publish additional collaborator code received later.

## Evidence boundary

This correction records the correspondence supplied by Colin and his planning agent on 2026-09-15. It does not claim
that email or Drive was independently re-read during implementation. Successful package builds, model-container
compatibility and truck validation are separate facts and require their own results.
