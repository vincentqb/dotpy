#!/usr/bin/env python3

import logging
import os
import re
from argparse import ArgumentParser
from pathlib import Path
from string import Template


def get_logger():
    class CallCounted:
        """Decorator to determine number of calls for a method"""

        def __init__(self, method):
            self.method = method
            self.counter = 0

        def __call__(self, *args, **kwargs):
            self.counter += 1
            return self.method(*args, **kwargs)

    class Formatter(logging.Formatter):
        GREY = "\x1b[38;20m"
        YELLOW = "\x1b[33;20m"
        RED = "\x1b[31;20m"
        BOLD_RED = "\x1b[31;1m"
        RESET = "\x1b[0m"
        FORMAT = "%(message)s"

        formats = {
            logging.DEBUG: GREY + FORMAT + RESET,
            logging.INFO: GREY + FORMAT + RESET,
            logging.WARNING: YELLOW + FORMAT + RESET,
            logging.ERROR: RED + FORMAT + RESET,
            logging.CRITICAL: BOLD_RED + FORMAT + RESET,
        }

        def format(self, record):
            format = self.formats.get(record.levelno)
            formatter = logging.Formatter(format)
            return formatter.format(record)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(Formatter())

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    logger.warning = CallCounted(logger.warning)  # Add counter for warnings
    return logger


def link(candidate, rendered, dotfile, dry_run, logger):
    """
    Link dotfiles to files in given profile directories.
    """

    # Create rendered file from template
    if candidate != rendered:
        with open(candidate, "r") as fp:
            content = Template(fp.read()).safe_substitute(os.environ)
        if not dry_run:
            with open(rendered, "w") as fp:
                fp.write(content)
        logger.debug(f"File {rendered} created.")

    # Create link
    if dotfile.exists():
        if dotfile.is_symlink():
            link = Path(os.readlink(str(dotfile))).expanduser().resolve()
            if link == rendered:
                logger.info(f"File {dotfile} links to {rendered} as expected")
            else:
                logger.warning(f"File {dotfile} exists and points to {link} instead of {rendered}")
        else:
            logger.warning(f"File {dotfile} exists but is not a link")
    else:
        if not dry_run:
            dotfile.symlink_to(rendered)
        logger.info(f"File {dotfile} created and linked to {rendered}")


def unlink(candidate, rendered, dotfile, dry_run, logger):
    """
    Unlink dotfiles linked to files in given profile directories.
    """
    if dotfile.exists():
        if dotfile.is_symlink():
            link = Path(os.readlink(str(dotfile))).expanduser().resolve()
            if link == rendered:
                if not dry_run:
                    dotfile.unlink()
                logger.info(f"File {dotfile} unlinked from {rendered}")
            else:
                logger.warning(f"File {dotfile} exists and points to {link} instead of {rendered}")
        else:
            logger.warning(f"File {dotfile} exists but is not a link")
    else:
        logger.warning(f"File {dotfile} does not exists")


def dry_run_then_wet_run(command, home, profiles, dry_run):
    """
    Manage links to dotfiles.
    """
    logger = get_logger()
    logger.setLevel(logging.INFO if dry_run else logging.WARNING)

    home = Path(home).expanduser().resolve()
    command = COMMANDS[command]

    def run(dry_run):
        if home.is_dir():
            for profile in profiles:
                profile = Path(profile).expanduser().resolve()
                if profile.is_dir():
                    for candidate in sorted(profile.glob("*")):
                        name = candidate.name
                        if name.startswith("."):
                            logger.debug(f"File {candidate} ignored.")
                        elif not name.endswith(".rendered"):
                            # Add dot prefix and replace template when needed
                            rendered = candidate.parent / re.sub(".template$", ".rendered", name)
                            dotfile = home / ("." + re.sub(".template$", "", name))
                            command(candidate, rendered, dotfile, dry_run, logger)
                else:
                    logger.warning(f"Profile {profile} does not exist")
        else:
            logger.warning(f"Folder {home} does not exist")

    # Always do a dry run first
    run(dry_run=True)

    if logger.warning.counter > 0:
        logger.error("There were conflicts: exiting without changing dotfiles.")
        raise SystemExit()

    if not dry_run:
        run(dry_run=dry_run)


def parse_arguments():
    parser = ArgumentParser(description=dry_run_then_wet_run.__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for key, func in COMMANDS.items():
        subparser = subparsers.add_parser(key, description=func.__doc__)
        subparser.add_argument("profiles", nargs="+")
        subparser.add_argument("--home", nargs="?", default="~")
        subparser.add_argument("-d", "--dry-run", default=False, action="store_true")
        subparser.add_argument("--no-dry-run", dest="dry_run", action="store_false")

    return vars(parser.parse_args())


COMMANDS = {"link": link, "unlink": unlink}
if __name__ == "__main__":
    dry_run_then_wet_run(**parse_arguments())