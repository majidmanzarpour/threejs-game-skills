# Physics Engine Selection

Three.js is a renderer. Physics runs in a separate world at a fixed timestep; mesh transforms are synchronized from body transforms afterwards.

## The ladder

1. **Custom collision** — arcade triggers, pickups, lanes, bullets, simple overlap tests, deterministic rails, endless runners, lane dodgers, transform-driven racers, sphere/box dogfights. Anywhere authored feel matters more than simulation.
2. **Rapier** — the default for serious browser games with real physics: mini golf, pool/snooker, pinball, marble racers, physics puzzles, platformers, moving platforms, ramps and slopes, character controllers, rigid-body stacks, destructible props, high-speed bodies needing CCD, sensor-heavy games.
3. **cannon-es** — lightweight JS-only fallback for small rigid-body scenes where avoiding WASM matters and collision complexity is low.
4. **Jolt** — advanced rigid-body work where its behavior is specifically wanted and WASM integration complexity is acceptable.
5. **Ammo.js/Bullet** — only when a project already depends on it.
6. **Matter.js** — 2D only.

Rapier is a Rust/WASM engine with official JS bindings: rigid bodies, colliders, sensors, collision events, forces/impulses, damping, axis locking, sleeping, and CCD.

Never collide against detailed visual meshes. Use primitive colliders, compound colliders, convex hulls, simplified triangle meshes for fixed level geometry only, and explicit sensor volumes. Imported GLB meshes get their own collision proxies.

## Rapier setup

```bash
npm install @dimforge/rapier3d-compat
```

```ts
import RAPIER from '@dimforge/rapier3d-compat';

await RAPIER.init();
const world = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
```

Fixed timestep with a clamped accumulator — the clamp is what keeps a tab-switch or a frame spike from spiralling:

```ts
const fixedDt = 1 / 60;
let accumulator = 0;

function update(deltaSeconds: number) {
  accumulator += Math.min(deltaSeconds, 0.1);
  while (accumulator >= fixedDt) {
    world.timestep = fixedDt;
    world.step();
    accumulator -= fixedDt;
  }
}
```

Bodies and colliders:

```ts
const body = world.createRigidBody(
  RAPIER.RigidBodyDesc.dynamic()
    .setTranslation(0, 2, 0)
    .setLinearDamping(0.25)
    .setAngularDamping(0.5)
);
world.createCollider(
  RAPIER.ColliderDesc.ball(0.5).setRestitution(0.6).setFriction(0.4),
  body
);
```

Sync in exactly one system:

```ts
const t = body.translation();
const r = body.rotation();
mesh.position.set(t.x, t.y, t.z);
mesh.quaternion.set(r.x, r.y, r.z, r.w);
```

Fast bodies need CCD explicitly (it costs extra, so use it only where tunneling is real):

```ts
RAPIER.RigidBodyDesc.dynamic().setCcdEnabled(true)
```

Sensors are silent without active events — this is the single most common trigger bug:

```ts
const sensor = RAPIER.ColliderDesc.ball(1)
  .setSensor(true)
  .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS);
```

## Architecture

- Physics ownership lives in `systems/PhysicsWorld` or `systems/CollisionSystem`, never in render code.
- Entities hold body handles and dispose them on restart.
- Update order: input intents → fixed physics → game state/collisions → VFX/camera/UI → render.
- Kinematic bodies for moving platforms and scripted obstacles; sensors for pickups, goals, holes, portals, checkpoints, damage zones.
- Keep a debug overlay for colliders, body counts, contact pairs, and velocity.
- Use sleeping and explicit body removal to avoid stale simulation state.

## Tuning

Tune in units that map cleanly to scene scale, with named constants. Set friction, restitution, damping, mass/density, gravity scale, and collision groups explicitly.

- Balls, mini-golf, pool, pinball: rolling friction/damping, restitution, cushion bounce, hole capture, max velocity.
- Arcade vehicles: combine kinematic control logic with collision response rather than relying on raw rigid-body simulation.
- Character controllers: capsule colliders, locked rotations, kinematic movement — unless ragdoll is actually wanted.

## Failure modes

Variable-delta physics feels nondeterministic · mesh and body drift apart because transforms are synced in two places · bodies survive a restart · detailed imported meshes make collision slow or wrong · fast projectiles tunnel without CCD · sensors fire nothing because active events are missing · kinematic platforms move visually but not physically.

Report engine used, body/collider counts, timestep, CCD bodies, sensors, and collision groups when physics is in scope.
