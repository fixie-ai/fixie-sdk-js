from . import commands


def test_update_agent_requirements_adds_fixie():
    new_requirements = commands._update_agent_requirements([], [])
    assert new_requirements == [commands.CURRENT_FIXIE_REQUIREMENT]


def test_update_agent_requirements_honors_specified_fixie():
    new_requirements = commands._update_agent_requirements([], ["fixieai"])
    assert new_requirements == ["fixieai"]


def test_update_agent_requirements_overrides_existing_fixie():
    new_requirements = commands._update_agent_requirements(
        ["fixieai", "fixieai == 0.0"], []
    )
    assert new_requirements == [commands.CURRENT_FIXIE_REQUIREMENT]


def test_update_agent_requirements_combines():
    new_requirements = commands._update_agent_requirements(
        ["package1", "package2"], ["package2", "package3"]
    )
    assert new_requirements == [
        "package1",
        "package2",
        commands.CURRENT_FIXIE_REQUIREMENT,
        "package3",
    ]
