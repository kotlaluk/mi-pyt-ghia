.. _files-label:

Configuration File Formats
==========================

GHIA, in both WEB and CLI versions, uses two types of configuration files -
files containing GitHub authentication infomration and files containing the
assignment rules that are used to match issues. Both types of configuration
files use standard configuration file syntax similar to Microsoft INI files.
This documentation page describes the expected content of these files.

Authentication files
--------------------

The authentication file should contain a section named ``github``. In this
section, there should be a key ``token``, and optionally a key ``secret``.

- ``token`` key should contain a GitHub `token <https://help.github.com/en/github/authenticating-to-github/   creating-a-personal-access-token-for-the-command-line>`_. The token is used
  instead of a password when communicating with GitHub API.
- if webhooks are `secured <https://developer.github.com/webhooks/securing/>`_
  while using GHIA WEB, the ``secret`` key should contain the set-up secret.
  This secret is used for validation of the received GitHub webhooks.

Example of an authentication configuration file:

.. code-block::

   [github]
   token=ffffffffffffffffffffffffffffffffffffffff
   secret=supersecret

.. NOTE::
   Both token and secret are information of a private character, similarly as
   a password, and should be handled accordingly.

Files with assignment rules
---------------------------

This type of file should contain a section named ``patterns`` and optionally,
a section named ``fallback``.

The ``patterns`` secition should contain the assignment rules (one per line),
where the key is the GitHub login name of the assignee, and the value is a
composition of the part of the issue to be matched and a regular expression
used for matching. The parts of the issue that can be matched are ``title``,
``text``, ``label``, and ``any``. See the example below for illustration.

The ``fallback`` section is optional, and can be used to specify a fallback
label that would be set on an issue if it has no assignees. The key ``label``
is expected to be found in this section, with the value naming the label to be
assigned.

Example of a file with assignment rules:

.. code-block:: none

   [patterns]
   ghia-anna=
       text:project management
       title:Unchanged
   ghia-peter=
       any:kanban
       any:flow
       title:set[- ]{0,1}up
       text:something awesome
   ghia-john=label:assign-john

   [fallback]
   label=Need assignment
