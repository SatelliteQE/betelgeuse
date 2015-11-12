from betelgeuse import parse_requirement_name


def test_parse_requirement_name():
    names = [
        'tests.foreman.api.test_compute_resource.ClassName.test_method',
        'tests.foreman.api.test_compute_resource.test_method',
    ]
    for name in names:
        assert parse_requirement_name(name) == 'Compute Resource'


