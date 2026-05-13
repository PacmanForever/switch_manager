# SwitchFlow Controller Implementation Plan

## 1. Purpose

This document defines the implementation plan for a new Home Assistant custom integration named `switch_manager` to be developed in `/home/pacman/Projectes/switch_manager`.

The integration should replace the current blueprint-style automation pattern with a conservative, compatibility-first runtime integration that is easier to maintain across future Home Assistant releases.

The plan is intentionally biased toward:

- simple code
- explicit runtime behavior
- standard Home Assistant APIs
- strong automated tests
- low-risk storage and migration strategy
- no unnecessary frontend customization

This is not a plan for the current Meteocat repository. It is a plan for a new repository.

## 2. Core Design Principles

### 2.1 Compatibility First

Prefer Home Assistant patterns that have been stable for a long time:

- `ConfigEntry`
- `OptionsFlow`
- standard entity selectors
- standard service registration
- explicit async listeners
- explicit storage with schema versioning

Avoid advanced or fragile patterns unless they become clearly necessary later.

### 2.2 Simple, Heavy, Explicit Code

The code should be "heavy" in the sense that behavior is obvious and explicit, not hidden behind abstractions.

That means:

- no clever dynamic rule engine
- no generated YAML automations
- no frontend-only solution
- no fake "global hub"
- no free-form service strings for critical actions

### 2.3 Conservative Scope For Version 1

Version 1 should only implement:

- one global configuration entry
- multiple controllers
- optional services
- runtime behavior equivalent to the current blueprint

Version 1 should not require hubs.

### 2.4 English Only

All code, comments, strings, documentation, tests, and identifiers must be written in English.

The original blueprint may remain in Catalan as source material only.

## 3. Functional Goal

The integration should manage one or more light or switch automation controllers.

Each controller represents one functional automation unit, for example:

- one bathroom light
- one hallway light with optional night light
- one staircase zone with two detector sensors

Each controller should be able to:

- react to main entity state changes
- react to night entity state changes
- react to detector sensors
- turn on the main entity or night entity based on rules
- optionally turn off other configured entities
- apply an illuminance threshold
- support delayed shutoff
- optionally send an alarm notification through a globally configured script

`main_entity` and `night_entity` may target either the `light` or `switch` domain.

## 4. Domain Model

The implementation should define three concepts.

### 4.1 Global Configuration

Global configuration is unique for the integration and belongs to the main config entry.

It contains shared references only.

Initial global fields:

- `smart_mode_entity`
- `night_mode_entity`
- `alarm_entity`
- `alarm_timer_entity`
- `alarm_notification_script_entity`

This configuration is edited through the integration setup and options flow.

### 4.2 Controller

A controller is the main functional object.

It stores only local behavior.

Initial controller fields:

- `id`
- `name`
- `enabled`
- `main_entity`
- `night_entity`
- `detector_sensor_1`
- `detector_sensor_2`
- `illuminance_sensor`
- `illuminance_threshold_entity`
- `wait_time`
- `turn_off_when_presence_clears`
- `activate_on_detection`
- `notify_with_alarm`
- `turn_off_entity_1`
- `turn_off_entity_2`
- optional `area_id`
- optional future `hub_id`

### 4.3 Hub

Hubs are not required in version 1.

If introduced later, hubs should be optional grouping objects only.

Hubs must not become a second inheritance layer for global configuration.

## 5. Configuration Model

### 5.1 Global Configuration Rules

Global configuration should be used for shared state references that are common across the house or across most controllers.

The following belong to the global level:

- smart mode helper
- night mode helper
- alarm entity
- alarm timer entity
- alarm notification script entity

These should be configured once, then read by every controller at runtime.

### 5.2 Controller Configuration Rules

Controller configuration should only contain local behavioral choices.

The following belong to the controller level:

- main entity
- night entity
- detector sensors
- illuminance sensor
- illuminance threshold entity
- wait time
- turn off when presence clears
- activate on detection
- notify with alarm
- secondary entities to turn off

`wait_time` must be required for every controller.

Even when `turn_off_when_presence_clears` is enabled, `wait_time` must still be configured and treated as a safety timeout.

Detector sensors may be either motion sensors or presence sensors.

In the UI, detector selector labels should use the text `detectors sensor 1` and `detectors sensor 2`.

### 5.3 No Global Hub

There must be no fake system hub for global settings.

Global configuration should live in the main config entry and be edited through:

- `Configure`
- `Options`

This keeps the model simpler and avoids forcing a false UI metaphor.

## 6. Runtime Behavior Mapping

The runtime behavior should match the current blueprint semantics as closely as possible while keeping the code explicit.

### 6.1 Global Gate

If `smart_mode_entity` is configured and it is not `on`, controller automation behavior should not execute.

Manual services may still be allowed depending on final service design.

### 6.2 Trigger Sources

Each controller listens to:

- `main_entity`
- `night_entity` if configured
- `detector_sensor_1` if configured
- `detector_sensor_2` if configured

### 6.3 Main Entity Changed

When the main entity changes:

1. If it turns `on`:
	- turn off `turn_off_entity_1` if configured
	- turn off `turn_off_entity_2` if configured
2. If it turns `off`:
	- if `night_entity` is configured and currently `on`, turn it off

### 6.4 Night Entity Changed

Version 1 does not need complex special behavior for manual night-entity state changes.

The runtime should still be aware of its state so that fallback and shutoff logic work correctly.

If the night entity is manually turned `on`, the controller may still restart its shutoff timer and apply the same secondary-entity turn-off behavior used by the normal activation path.

### 6.5 Detection Triggered

When detection is reported by either configured detector sensor, the runtime should evaluate behavior in this order:

1. Alarm notification path
2. Detection-based activation path
3. Delayed shutoff scheduling

### 6.6 Alarm Notification Path

The alarm notification path runs only if all of the following are true:

- controller `notify_with_alarm` is `true`
- a global `alarm_entity` is configured
- the alarm entity is in the target armed state
- `alarm_timer_entity` is absent or idle

If the conditions are met:

1. turn on the main entity
2. call the global notification script if configured

### 6.7 Detection-Based Activation Path

The detection activation path runs only if `activate_on_detection` is enabled.

Its evaluation order should be:

1. night mode
2. illuminance rule
3. default main-entity activation

### 6.8 Night Mode Rule

If `night_mode_entity` is configured and `on`:

1. if `main_entity` is `off`
2. and `night_entity` is absent or `off`
3. turn on `night_entity` if configured
4. otherwise turn on `main_entity`

If supporting a colored night light creates too much branching between `switch` and `light`, defer that feature until later.

### 6.9 Illuminance Rule

If `illuminance_sensor` is configured and has a known value:

1. compare it with `illuminance_threshold_entity` if configured
2. otherwise compare with a built-in default threshold
3. if below threshold and `main_entity` is `off`, turn on `main_entity`

If `illuminance_sensor` is configured and has a known value above threshold, detection-based activation should be blocked for that cycle.

If the illuminance sensor is configured but unreadable or unavailable, treat that as a configuration problem for logging and Repairs visibility, then fall back safely to the standard activation path.

Do not add formulas, templates, or complex derived thresholds in version 1.

### 6.10 Default Activation Rule

If no earlier rule handled activation and `main_entity` is `off`, turn on `main_entity`.

### 6.11 Delayed Shutoff Rule

After a successful activation path:

1. always start or restart a safety timer using the configured `wait_time`
2. if `turn_off_when_presence_clears` is `true` and all configured detector sensors are presence-style sensors, also wait until all configured detector sensors are clear
3. if presence clears before the safety timer expires, turn off `main_entity`
4. and turn off `night_entity` if configured
5. then cancel the pending safety timer for that activation cycle
6. if the safety timer expires first and the controlled entity is still `on`, turn off `main_entity`
7. and turn off `night_entity` if configured

This flag is intended for presence-style detector sensors that remain `on` while presence is continuously detected.

When `turn_off_when_presence_clears` is enabled:

- automatic shutoff may happen before `wait_time` only if all configured detector sensors are presence-style sensors
- the controller must turn off as soon as all configured detector sensors are clear
- if multiple detector sensors are configured, all of them must be clear before shutoff
- if one configured detector sensor is not presence-style, the controller must fall back to the normal detection-based delayed shutoff path
- if both configured detector sensors are presence-style, the controller should behave as a presence-based controller for shutoff timing
- the configured `wait_time` must still act as a hard upper bound for how long the entity may remain on
- if the entity is turned off because presence cleared first, the safety timer for that activation cycle should be cancelled

The controller should behave like a restart-style automation:

- stale pending timers must be cancelled on retrigger
- the most recent relevant trigger should win

## 7. Alarm Notification Design

### 7.1 Script Reference

Do not store a free-form service string such as `script.send_alarm_message`.

Instead, store a selected entity of domain `script` in global configuration.

### 7.2 Invocation Strategy

The runtime should call the selected script using standard Home Assistant script invocation.

### 7.3 Payload Contract

Define a stable payload contract from the start.

Minimum payload:

- `message`

Optional payload fields if easy to support reliably:

- `controller_name`
- `trigger_entity_id`
- `area_name`

### 7.4 Missing Script

If no global notification script is configured:

- do not raise an error
- simply skip notification

## 8. Storage Strategy

### 8.1 Global Settings Storage

Store global configuration in the main config entry.

### 8.2 Controller Storage

Use a dedicated versioned storage layer for controller records.

This is preferred over forcing all controller data into one large options blob.

### 8.3 Schema Versioning

The controller storage format must have a schema version from day one.

That allows safe migrations later.

### 8.4 Stable IDs

Each controller must have a stable internal ID that is independent from its display name.

Display names may change later without breaking runtime references.

## 9. Config Flow And Options Flow

### 9.1 Initial Config Flow

The initial setup flow should:

1. create the main config entry
2. collect global shared references
3. validate entity domains conservatively
4. allow optional fields to remain empty

Controller entity selectors should accept both `switch` and `light` for `main_entity` and `night_entity`.

### 9.2 Options Flow

The options flow should be the main operational configuration surface.

It should provide:

1. edit global settings
2. list controllers
3. add controller
4. edit controller
5. delete controller
6. enable controller
7. disable controller

Controller validation should require `wait_time` and reject a controller configuration that omits it.

Use a menu-based flow if that keeps the code simpler and more maintainable.

## 10. Runtime Architecture

### 10.1 Main Runtime Manager

Create a central runtime manager responsible for:

- loading global settings
- loading controllers
- registering listeners
- dispatching triggers
- managing reloads
- cleaning up listeners and tasks

### 10.2 Controller Runtime Module

Each controller should be handled by explicit controller runtime logic.

This can be a dedicated class or module, but it should remain easy to trace.

### 10.3 Separation Of Responsibilities

Keep clear boundaries between:

- storage
- config flow
- runtime evaluation
- service execution
- optional entity exposure

## 11. Entity Surface

### 11.1 Minimal Version 1

Version 1 does not need many entities.

The integration can work with internal runtime management and services.

### 11.2 Optional Later Entities

Only add entities later if they provide real operational value, for example:

- controller enabled switch
- last trigger diagnostic sensor
- reset timer button

Avoid decorative entities.

## 12. Services

Version 1 should expose only a small, stable service surface.

Service surface for 0.1:

- `enable_controller`
- `disable_controller`
- `reset_controller_timer`
- `force_turn_on`
- `force_turn_off`

Services should target controllers by stable internal ID.

These services should be documented in `services.yaml` so Home Assistant can expose field help in the UI.

## 13. Repository Structure

Recommended files for version 1:

- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/manifest.json`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/__init__.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/config_flow.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/const.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/models.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/storage.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/manager.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/controller.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/issues.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/services.py`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/services.yaml`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/strings.json`
- `/home/pacman/Projectes/switch_manager/custom_components/switch_manager/translations/en.json`
- `/home/pacman/Projectes/switch_manager/.github/workflows/tests.yml`
- `/home/pacman/Projectes/switch_manager/.github/workflows/validate_hacs.yml`
- `/home/pacman/Projectes/switch_manager/.github/workflows/validate_hassfest.yml`
- `/home/pacman/Projectes/switch_manager/tests/conftest.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_config_flow.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_options_flow_global.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_options_flow_controller.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_controller_runtime.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_alarm_notifications.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_illuminance_behavior.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_night_mode_behavior.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_delayed_shutoff.py`
- `/home/pacman/Projectes/switch_manager/tests/component/test_services.py`
- `/home/pacman/Projectes/switch_manager/tests/unit/test_storage_migrations.py`
- `/home/pacman/Projectes/switch_manager/README.md`
- `/home/pacman/Projectes/switch_manager/CHANGELOG.md`
- `/home/pacman/Projectes/switch_manager/requirements-test.txt`
- `/home/pacman/Projectes/switch_manager/pytest.ini`

## 14. Quality Target

The project should follow the spirit of the current repository quality standard.

Target:

- practical Home Assistant Silver-level discipline
- strong automated coverage from the beginning
- Hassfest readiness
- HACS readiness
- robust error handling
- explicit documentation

The exact official percentage target may evolve, but the repository should be designed to keep high coverage and low ambiguity from the start.

## 15. Testing Strategy

### 15.1 Config Tests

Test:

- initial setup flow
- domain validation
- optional fields
- controller validation rejects missing `wait_time`
- controller validation accepts `turn_off_when_presence_clears` only as a boolean field
- config entry reload and unload

### 15.2 Controller Storage Tests

Test:

- create
- read
- update
- delete
- enable and disable
- `wait_time` persistence
- `turn_off_when_presence_clears` persistence
- schema migration

### 15.3 Runtime Tests

Test:

- smart mode disabled
- main entity on path
- main entity off path
- detection from detector sensor 1
- detection from detector sensor 2
- alarm notification path
- local notification opt-out
- missing notification script
- night mode path
- illuminance threshold path
- default activation path
- delayed shutoff
- presence-clear immediate shutoff
- mixed presence and detector sensors fall back to delayed shutoff
- safety timeout turns entity off even if presence sensor remains stuck on
- presence-clear shutoff cancels the pending safety timer
- detector-clear waiting
- stale timer cancellation
- rapid retrigger behavior

### 15.4 Service Tests

Test:

- valid controller IDs
- invalid controller IDs
- disabled controller behavior
- reset timer behavior

### 15.5 Issue Visibility Tests

Test:

- configured-but-unavailable entities create a warning issue
- warning issues are cleared when the entity becomes available again
- unconfigured optional entities do not create issues

### 15.6 Documentation Consistency

Review that documentation matches:

- config flow
- options flow
- runtime behavior
- supported limitations

## 16. Documentation Requirements

The README should explain:

1. what the integration does
2. that the README should follow a structure and level of completeness similar to the Meteocat repository README, but in English only
2. why there is no global hub
3. the difference between global configuration and controllers
4. how to migrate manually from the blueprint
5. example configurations
6. known limitations of version 1

The README should be intentionally close in spirit to the Meteocat documentation style:

- clear project introduction
- feature overview
- installation section
- configuration section
- behavior notes
- examples
- testing or quality notes
- versioning or release notes summary if useful

For `switch_manager`, only one README is required in version 1:

- `README.md` in English

There is no requirement to maintain Catalan or Spanish translations for the new repository in version 1.

Recommended examples:

- bathroom controller
- hallway controller with night light
- staircase controller with two detector sensors

## 17. Deferred Features

The following should be deferred until after version 1 is stable:

- hubs
- subentries if not clearly needed
- colored night-light payloads if they complicate the core
- rich diagnostic entities
- automatic blueprint import
- complex inheritance or presets

## 18. Execution Milestones

### Milestone 1: Repository Scaffold

Create the repository skeleton and base files.

Deliverables:

- integration folder layout
- minimal manifest
- empty config flow
- README
- CHANGELOG
- pytest setup
- requirements-test
- initial tests layout

Verification:

- manifest is valid
- tests are collected
- repository structure is ready for Hassfest and HACS validation
- CI workflows exist for tests, Hassfest, and HACS validation

### Milestone 2: Global Configuration Model

Implement the main config entry and first setup flow.

Deliverables:

- global settings form
- domain validation
- clean setup and unload

Verification:

- valid creation works
- invalid domains fail clearly
- optional fields can stay empty

### Milestone 3: Controller Storage Model

Implement storage for controller records.

Deliverables:

- versioned storage
- stable controller IDs
- migration-ready schema

Verification:

- CRUD works
- `wait_time` and `turn_off_when_presence_clears` persist correctly
- migration tests pass

### Milestone 4: Options Flow For Controller Management

Implement the options flow menu and controller lifecycle actions.

Deliverables:

- edit global settings
- add controller
- edit controller
- delete controller
- enable and disable controller

Verification:

- all menu paths and validation paths are covered
- controller forms require `wait_time`
- controller forms correctly save and reload `turn_off_when_presence_clears`

### Milestone 5: Runtime Manager Foundation

Implement the runtime manager, listener registration, and cleanup logic.

Deliverables:

- runtime bootstrap
- listener registration
- reload and unload cleanup

Verification:

- multiple controllers can be loaded and cleaned up safely

### Milestone 6: Main Entity And Secondary Shutoff Behavior

Implement the main-entity state handling logic.

Verification:

- secondary entities are turned off when expected
- night entity is turned off when the main entity turns off

### Milestone 7: Detection Activation Behavior

Implement detector handling with the correct evaluation order.

Verification:

- detector triggers produce the expected activation path
- smart mode off blocks runtime automation

### Milestone 8: Alarm Notification Behavior

Implement local notification gating plus global script invocation.

Verification:

- alarm armed plus idle timer triggers the script
- disabled local notification prevents script invocation
- missing script is handled safely

### Milestone 9: Night Mode And Illuminance Logic

Implement night-mode preference and illuminance threshold logic.

Verification:

- night-entity preference works
- fallback to main entity works
- threshold logic behaves correctly

### Milestone 10: Delayed Shutoff Engine

Implement restart-style delayed shutoff.

Verification:

- retriggers cancel stale timers
- shutdown waits for detector sensors to clear
- presence-clear mode skips `wait_time` only when all configured detector sensors are presence-style
- mixed sensor types fall back to normal delayed shutoff
- `wait_time` always acts as a safety timeout
- presence-clear shutoff cancels the pending safety timer

### Milestone 11: Manual Services

Implement the small service surface.

Verification:

- valid and invalid service targets are handled correctly
- service fields are documented through `services.yaml`

### Milestone 12: Documentation And Migration Guide

Document configuration, migration from blueprint instances, limitations, and examples.

Deliverables:

- `README.md` written in English only
- README structure modeled after the Meteocat README level of clarity and completeness
- installation instructions
- configuration model explanation
- global vs controller explanation
- manual migration guide from blueprint inputs to controller fields
- usage examples
- limitations and compatibility notes
- testing or quality section

Verification:

- documentation matches the implemented behavior
- README is complete enough to stand on its own in the same way the Meteocat README does, without requiring extra language variants

### Milestone 13: Coverage Hardening

Add missing tests for edge cases and maintenance-sensitive paths.

Verification:

- the project reaches a strong practical Silver-level test baseline

### Milestone 14: Post-v1 Evaluation

Only after the core is stable, evaluate:

- hubs
- subentries
- diagnostics
- colored night-light behavior

## 19. Locked Decisions

The following decisions are already agreed and should not be reopened unless implementation reveals a real blocker:

1. The work belongs in `/home/pacman/Projectes/switch_manager`.
2. The implementation must be in English.
3. There is no global hub.
4. Shared settings live in one main config entry.
5. `notify_with_alarm` is controller-local.
6. The notification action is a globally configured `script` entity reference.
7. Version 1 prioritizes simplicity and compatibility over broader feature scope.
8. Hubs are optional and postponed.

## 20. First Implementation Task

Before writing production code, keep this file updated as the source of truth for architecture and scope.

If implementation decisions change, update this plan first, then update code.

