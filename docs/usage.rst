Usage
=====

GHIA can be used as **CLI** or **WEB** application.

:ref:`cli-label` allows to process GitHub issues for the specified repositories
in batches. User can specify a file containing assignment rules (regular
expressions) that would be matched against issue title, body, label, or any of
these elements. If an issue from the repository matches the rule, the specified
user is assigned to the issue.

:ref:`web-label` allows to process GitHub issues in real-time, once they are
created or changed in a GitHub repository. For this, a user needs to set up
a GitHub webhook in the repository. Once the webhook is set up, the running web
application will receive an information about change in the issues, and will
assign users to the issue according to the loaded configuration. The application
is able to load a similar file containing assignment rules as the CLI part.
Furthermore, currently running configuration is presented as a static webpage.

.. toctree::
   :maxdepth: 4

   usage/cli
   usage/web
   usage/files
