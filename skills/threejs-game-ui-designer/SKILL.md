---
name: threejs-game-ui-designer
description: "Design premium Three.js game UI: HUDs, menus, overlays, pause/win/lose screens, settings, icon controls, touch UI, typography, responsive layout, safe areas, text fit, and UI/world cohesion."
---

# Three.js Game UI Designer

Make game UI intentional, readable, responsive, and specific to the genre.

Preserve the user's requested scope and style. For a narrow HUD fix, retain the existing design and check the changed state and target viewports. For a complete UI pass, use the full workflow below. Mobile input is required when mobile is a target, not because a desktop-only game has UI.

## Reference

`references/ui-patterns.md` — hierarchy and required states, HUD zones, menus, touch controls, responsive constraints, style cohesion, and state wiring. Read it before designing HUDs, menus, overlays, touch controls, or responsive layout.

Load `threejs-image-generator` when logos, icons, GUI art, faction marks, menu backgrounds, or 2D HUD assets would raise the quality. `threejs-3d-generator` only for genuine 3D menu objects and diegetic props, not flat HUD elements.

## Workflow

1. Capture desktop and mobile screenshots of what exists.
2. Inventory the UI states: gameplay, pause, settings, fail and retry, win or milestone, loading, touch controls.
3. Set the hierarchy: survival and status, then objective, then feedback, then flavor.
4. Replace utility stat cards with authored clusters, meters, badges, icons, alerts, and modal states.
5. Use stable dimensions, safe-area padding, text-fit constraints, and hover/pressed/focus/disabled states.
6. Wire UI to game state rather than duplicating game rules inside UI code.
7. Check text fit and overlap with the longest likely values, safe areas, touch targets, and real state changes on both viewports.

## What goes wrong

A generic dashboard of stat cards · UI covering the player, threats, or the next decision · text that shifts and clips on mobile · decorative panels that reduce readability · touch controls that look right but emit no intents.

## Report

UI intent and states covered, files changed, target-viewport screenshots, text-fit and overlap findings, safe-area and touch-target evidence where applicable, and remaining risks. Feed these results into the lead's consolidated pass rather than rerunning unchanged game-wide checks.
