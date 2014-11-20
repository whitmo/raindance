from mock import Mock


def test_cli():
    from raindance import cli
    cli.make_context(Mock(), Mock())
    cli.genopts(Mock())
    cli.prep_export(Mock())
    cli.update_manifest(Mock())
    cli.mirror(Mock())


def test_parse_spec():
    from raindance import cli
    assert cli.parse_spec('wat') == ('wat', None)
    assert cli.parse_spec('wat/huh') == ['wat', 'huh']
