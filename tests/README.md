# Tests

## Scope

The test suite is split into:

- `tests/unit` for isolated logic such as models and storage normalization
- `tests/component` for Home Assistant-facing behavior such as flows, services, issues, and runtime paths

## Local Commands

Compile all Python sources:

```bash
/home/pacman/Projectes/switch_manager/.venv/bin/python -m compileall custom_components tests
```

Run the currently validated local slice:

```bash
/home/pacman/Projectes/switch_manager/.venv/bin/python -m pytest tests/unit/test_models.py tests/unit/test_storage_migrations.py tests/component/test_services.py tests/component/test_issues.py tests/component/test_config_flow.py tests/component/test_controller_runtime.py tests/component/test_alarm_notifications.py tests/component/test_illuminance_behavior.py tests/component/test_delayed_shutoff.py -q
```

## What Current Tests Cover

- model normalization and required fields
- storage payload normalization and migration-ready behavior
- service registration and validation errors
- Repairs issue creation and cleanup
- config flow and controller options-flow behavior
- controller runtime timing and fallback logic
- alarm notification path
- illuminance gating
- mixed detector early shutoff behavior