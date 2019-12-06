.. _cli-label:

CLI Application
===============

GHIA in CLI mode processes all issues for the specified repository. After
:ref:`installation<installation-label>` of the GHIA package, the interface can
be invoked by calling ``ghia``.

GHIA CLI offers following options (can be viewed by calling ``ghia --help``:

.. code-block:: console

    Usage: ghia [OPTIONS] REPOSLUG

      CLI tool for automatic issue assigning of GitHub issues

    Options:
      -s, --strategy [append|set|change]
                                      How to handle assignment collisions.
                                      [default: append]
      -d, --dry-run                   Run without making any changes.
      -a, --config-auth FILENAME      File with authorization configuration.
                                      [required]
      -r, --config-rules FILENAME     File with assignment rules configuration.
                                      [required]
      --help                          Show this message and exit.

**REPOSLUG** is the reposlug of the GitHub repository that should be processed,
in user/repository format, e.g. "kotlaluk/mi-pyt-ghia".

**strategy** is the strategy which is applied while changing issue assignees.
This is important especially if the issue had some assignees previously:

- *append* (default) will add new assignees to the already existing assignees
- *set* will add assignees only in case the issue was not assigned to anyone
- *change* will remove all existing assignees and assign the issue to the users
  matched by the rules

**config-auth** is a file containing information required for GitHub
authentication and authorization. See the section :ref:`files-label` for the
description of the format for this file.

**config-rules** is a file containing the matching rules for issue assignment.
See the section :ref:`files-label` for the description of the format for this
file.

**dry-run** allows to run the application without actually making any changes
in the GitHub repository. However, the application will print the output
normally, as it would be making changes. This can be useful, for example, for
testing the assignment rules.
