# Game UI Patterns

Build the game interface, not a web dashboard.

## Hierarchy and states

Order: survival/status → objective/progress → immediate feedback → flavor. Reach for meters, icons, reticles, badges, alert strips, cooldown rings, inventory slots, minimaps, diegetic labels, and compact clusters before generic stat cards. UI stays outside the play path and clear of threats, pickups, the player, and the next decision, and it carries the world's art direction through material cues, color roles, icon shapes, and motion.

Inventory the states before designing: gameplay HUD, pause/resume, settings (audio/accessibility) when useful, fail/retry, win or milestone, loading/empty/error when assets load async, touch controls when mobile is in scope, and debug UI gated separately. A premium game has more than one HUD state.

Where an icon, affordance, or direct interaction can carry the meaning, use it instead of text explaining an obvious control.

## HUD composition

Zones: top-left for objective, wave, distance, timer, route · top-right for score, currency, combo, inventory, pause · bottom corners for touch movement and action controls · center-top or near-player for short event banners, combos, warnings · near-world for diegetic prompts, target markers, offscreen indicators.

- Fixed-width numeric containers for score, timer, ammo, speed, health, best — values that change width shift layout mid-play.
- Icons plus short labels for unfamiliar resources; meter fills for quantities read at a glance.
- Consistent alert colors across danger, reward, shield, boost, objective, disabled.
- Brief state animation: count-up, meter fill, pulse, slide, snap, ring cooldown.
- Never stack multiple large banners over the play path.

## Menus and overlays

Primary action first (resume, retry, continue, next), then secondary (settings, quit, restart, level select). Restrained panels with meaningful geometry, borders, ticks, glow accents, and material cues — not nested cards or a marketing hero layout inside a game. Icon buttons for pause, sound, restart, fullscreen, settings. Focus, hover, pressed, and disabled states on everything interactive. Debug panels sit behind a dev flag or query param.

## Touch controls

- Pointer events, emitting the same game intents as keyboard and mouse.
- Handle `pointerup`, `pointercancel`, `lostpointercapture`, blur, and visibility change — a missed cancel leaves a control stuck down.
- Safe-area insets; touch targets around 44 CSS pixels; adjacent controls separated enough to prevent mispresses.
- `touch-action` scoped to control regions and the game surface, so page scroll cannot steal input.
- Controls clear of HUD warnings and the play path.

## Responsive constraints

Stable dimensions from CSS variables, `clamp`, grid tracks, fixed icon slots, and fixed-width numerals. Don't scale text purely with viewport width, and avoid negative letter spacing. Check desktop, laptop, narrow tablet, and phone, using the longest likely values — high score, long labels, multi-digit timers. Nothing clipped, overlapping, unreadably small, or shifting as values change; menus stay reachable on every viewport.

## Style and cohesion

Match the genre: arcade racers need speed and status readability, fighters need health/round/impact hierarchy, exploration needs inventory and objective clarity. A limited status palette over neutral surfaces. Connect UI motifs to world decals, faction marks, vehicle panels, pickups, and hazards. One-note purple/blue gradient UI needs a reason from the game world.

## Generated 2D assets

`threejs-image-generator` covers what hand-coded CSS and icons cannot: faction logos, team crests, title marks; pickup/ability/weapon/inventory/achievement/objective icons; hazard signs, decals, lane glyphs, cockpit labels, item badges; menu, loading, and background plates; GUI material references such as glass panels, metal frames, holographic strips, parchment, tactical screens.

`threejs-3d-generator` is for UI that needs a real 3D object — rotating character preview, vehicle garage, weapon inspect, trophy, diorama, diegetic menu prop.

## State wiring

UI reads from a single source of truth and dispatches intents rather than mutating simulation internals. It updates on pause, restart, resize, orientation, mute, fail/win, score, health, boost, combo, inventory, and accessibility changes — with no stale values after a restart.

## Recurring failures

Generic stat-card HUD · nested cards and oversized decorative panels · UI covering threats, pickups, player, or the next decision · text explaining controls that should have been designed as affordances · ignored safe areas · touch controls that look right but emit nothing · layout shifting as values change · debug UI shipped as player UI.
