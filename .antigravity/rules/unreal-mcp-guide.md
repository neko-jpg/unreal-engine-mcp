# Unreal Engine MCP Operation Guide (Antigravity Edition)

## 1. Basic Rules

* **Actor Name Management**: After executing commands such as `spawn_actor`, always retrieve the `name` (the actual actor name) included in the response. Use this name for all subsequent operations (movement, material changes, deletion, etc.).
* **Batch Operations**: When spawning a large number of actors, avoid calling `spawn_actor` in a loop. Instead, use `batch_spawn_actors` (if implemented) whenever possible.

## 2. Standard Parameters

### Color Specification (RGBA)

Colors are specified as a list `[R, G, B, A]`, where each value ranges from `0.0` to `1.0`.

* **Red**: `[1.0, 0.0, 0.0, 1.0]`
* **Green**: `[0.0, 1.0, 0.0, 1.0]`
* **Blue**: `[0.0, 0.0, 1.0, 1.0]`
* **White**: `[1.0, 1.0, 1.0, 1.0]`
* **Black**: `[0.0, 0.0, 0.0, 1.0]`
* **Purple**: `[0.5, 0.0, 1.0, 1.0]`

### Standard Mesh Paths

* **Sphere**: `/Engine/BasicShapes/Sphere.Sphere`
* **Cube**: `/Engine/BasicShapes/Cube.Cube`
* **Cylinder**: `/Engine/BasicShapes/Cylinder.Cylinder`
* **Plane**: `/Engine/BasicShapes/Plane.Plane`

## 3. Physics Settings

To enable physical behavior, the following parameters are recommended:

* `simulate_physics`: `True`
* `gravity_enabled`: `True`
* `linear_damping`: `0.1` (for natural bouncing behavior)
* `angular_damping`: `0.1`

## 4. Troubleshooting

* **Connection Errors**: Ensure Unreal Editor is running, the plugin is enabled, and TCP port `55557` (or the configured port) is open.
* **Scale is 0**: Check whether the scale was explicitly set to zero during spawning, or if the actor name is incorrect.
* **Name Conflicts**: When spawning new actors, use unique names such as `MySphere_01`, or rely on the engine’s auto-naming and confirm via the response.
