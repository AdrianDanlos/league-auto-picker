LANE_KEYS = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"}
PREFERRED_ROLE_KEYS = LANE_KEYS | {"MID", "SUP", "SUPPORT", "ADC", "BOT"}
SUMMS_ROLE_KEYS = {"top", "jungle", "middle", "bottom", "utility"}


def _validate_lane_champion_list_map(section_name, value, errors):
    if not isinstance(value, dict):
        errors.append(f"'{section_name}' must be an object mapping lanes to champion lists.")
        return

    for lane, champions in value.items():
        if str(lane).upper() not in LANE_KEYS:
            errors.append(
                f"'{section_name}.{lane}' is not a supported lane. "
                f"Use one of: {', '.join(sorted(LANE_KEYS))}."
            )
            continue
        if not isinstance(champions, list):
            errors.append(f"'{section_name}.{lane}' must be a list of champion names.")
            continue
        for idx, champ in enumerate(champions):
            if not isinstance(champ, str) or not champ.strip():
                errors.append(
                    f"'{section_name}.{lane}[{idx}]' must be a non-empty champion name string."
                )


def _validate_nested_champion_map(section_name, value, errors):
    if not isinstance(value, dict):
        errors.append(f"'{section_name}' must be an object.")
        return

    for lane, counters_by_champion in value.items():
        if str(lane).upper() in {"DEFAULT", "RANDOM_MODE"}:
            # Those are validated elsewhere.
            continue
        if str(lane).upper() not in LANE_KEYS:
            errors.append(
                f"'{section_name}.{lane}' is not a supported lane. "
                f"Use one of: {', '.join(sorted(LANE_KEYS))}."
            )
            continue
        if not isinstance(counters_by_champion, dict):
            errors.append(
                f"'{section_name}.{lane}' must map your champion names to counter lists."
            )
            continue

        for champion, counter_list in counters_by_champion.items():
            if not isinstance(champion, str) or not champion.strip():
                errors.append(
                    f"'{section_name}.{lane}' has an invalid champion key: '{champion}'."
                )
                continue
            if not isinstance(counter_list, list):
                errors.append(
                    f"'{section_name}.{lane}.{champion}' must be a list of enemy champion names."
                )
                continue
            for idx, enemy in enumerate(counter_list):
                if not isinstance(enemy, str) or not enemy.strip():
                    errors.append(
                        f"'{section_name}.{lane}.{champion}[{idx}]' must be a non-empty champion name string."
                    )


def _validate_summs(summs, errors):
    if not isinstance(summs, dict):
        errors.append("'summs' must be an object.")
        return

    for role, champions in summs.items():
        if str(role).lower() not in SUMMS_ROLE_KEYS:
            errors.append(
                f"'summs.{role}' is not a supported role. "
                f"Use one of: {', '.join(sorted(SUMMS_ROLE_KEYS))}."
            )
            continue

        if not isinstance(champions, dict):
            errors.append(f"'summs.{role}' must map champion names to spell settings.")
            continue

        for champion_name, spell_config in champions.items():
            if not isinstance(champion_name, str) or not champion_name.strip():
                errors.append(f"'summs.{role}' has an invalid champion key.")
                continue
            if not isinstance(spell_config, dict):
                errors.append(
                    f"'summs.{role}.{champion_name}' must be an object with spell1Id/spell2Id."
                )
                continue

            spell1 = spell_config.get("spell1Id")
            spell2 = spell_config.get("spell2Id")
            if not isinstance(spell1, int) or spell1 <= 0:
                errors.append(
                    f"'summs.{role}.{champion_name}.spell1Id' must be a positive integer."
                )
            if not isinstance(spell2, int) or spell2 <= 0:
                errors.append(
                    f"'summs.{role}.{champion_name}.spell2Id' must be a positive integer."
                )


def validate_config(config):
    """
    Validate config.json shape and core value types.

    Returns:
        tuple[list[str], list[str]]: (errors, warnings)
    """
    errors = []
    warnings = []

    if not isinstance(config, dict):
        return ["Top-level config must be a JSON object."], warnings

    required_sections = [
        "bans",
        "picks",
        "summs",
        "random_mode_active",
        "autoselect_runes",
        "preferred_role",
        "messages",
    ]
    for key in required_sections:
        if key not in config:
            errors.append(f"Missing required config key: '{key}'.")

    if errors:
        return errors, warnings

    _validate_lane_champion_list_map("bans", config.get("bans"), errors)

    picks = config.get("picks")
    if not isinstance(picks, dict):
        errors.append("'picks' must be an object.")
    else:
        _validate_nested_champion_map("picks", picks, errors)
        _validate_lane_champion_list_map("picks.DEFAULT", picks.get("DEFAULT"), errors)
        _validate_lane_champion_list_map(
            "picks.RANDOM_MODE", picks.get("RANDOM_MODE"), errors
        )

    _validate_summs(config.get("summs"), errors)

    random_mode_active = config.get("random_mode_active")
    if not isinstance(random_mode_active, bool):
        errors.append("'random_mode_active' must be true or false.")

    autoselect_runes = config.get("autoselect_runes")
    if not isinstance(autoselect_runes, bool):
        errors.append("'autoselect_runes' must be true or false.")

    preferred_role = config.get("preferred_role")
    if not isinstance(preferred_role, str) or not preferred_role.strip():
        errors.append("'preferred_role' must be a non-empty string.")
    elif preferred_role.strip().upper() not in PREFERRED_ROLE_KEYS:
        errors.append(
            "'preferred_role' must be one of: "
            f"{', '.join(sorted(PREFERRED_ROLE_KEYS))}."
        )

    messages = config.get("messages")
    if not isinstance(messages, list):
        errors.append("'messages' must be a list of strings.")
    else:
        for idx, msg in enumerate(messages):
            if not isinstance(msg, str):
                errors.append(f"'messages[{idx}]' must be a string.")

    if not config.get("messages"):
        warnings.append(
            "No chat messages configured. Champ-select message sending will be skipped."
        )

    if "cycle_counter_hotkey" in config:
        cycle_counter_hotkey = config.get("cycle_counter_hotkey")
        if (
            not isinstance(cycle_counter_hotkey, str)
            or not cycle_counter_hotkey.strip()
        ):
            errors.append(
                "'cycle_counter_hotkey' must be a non-empty string (example: 'f8')."
            )

    return errors, warnings
