"""Simple wrapper script that registers the Usd-Optimize validators and then
redirects to the `usd_validation_nvidia` CLI entry point.

The wrapper also understands a `--verbose` flag: several Usd Optimize rules
normally report a single aggregate count anchored at the stage root, so the
failing prim paths never reach the CSV ``Location`` column. ``--verbose`` makes
those rules also emit one issue per failing prim. The flag is consumed here
(the upstream CLI does not know about it) and translated into a
``set_verbose(True)`` call; the equivalent engine-parameter
(``--parameter VERBOSE=true`` / ``--parameter <Rule>.VERBOSE=true``) and
``USD_OPTIMIZE_VALIDATOR_VERBOSE=1`` env var also work.
"""
import sys


def main() -> int:
    from usd_validation_nvidia import cli_main
    import usd_optimize.validators

    usd_optimize.validators.register_all()

    # Consume our own --verbose before delegating; the upstream cli_main() does
    # not define it, so leaving it in argv would error.
    if "--verbose" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--verbose"]
        usd_optimize.validators.set_verbose(True)

    return cli_main()

if __name__ == "__main__":
    sys.exit(main())
