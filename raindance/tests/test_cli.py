from mock import Mock

def test_cli():
    from raindance import cli
    cli.make_context(Mock(), Mock())
    cli.genopts(Mock())
    cli.prep_export(Mock())
    cli.update_release_manifest(Mock())
