Examples
========

This page shows examples of applying different matching strategies on a GitHub
issue, with usage of a file providing assignment rules.

.. testsetup::

   import json
   from ghia.github import create_issue, process_issue
   from ghia.validators import validate_rules

   with open("../tests/fixtures/issues_example.json") as f:
       payload = json.load(f)
       issue = create_issue(payload["issue"])

   rules = validate_rules(None, None, "../tests/fixtures/rules.no_fallback.cfg")

We would like to process the following GitHub issue:

.. testcode::
   :hide:

   print("Title:", issue.title)
   print("Body:", issue.body)
   print("Labels:", issue.labels)
   print("Assignees:", issue.assignees)

.. testoutput::

   Title: Spelling error in the README file
   Body: It looks like you accidently spelled 'commit' with two 't's.
   Labels: ['bug']
   Assignees: {'Codertocat'}

And we have loaded the following configuration file:

.. code-block:: none

   [patterns]
   ghia-jane=
       text:network(?:ing)?
       text:TCP|UDP
       text:commit
   ghia-anna=
       text:requests\s+library

As visible, the issue currently has one assignee. The matching rule for the
user *ghia-jane* contains phrase "commit" that will be found in the issue body,
and thus *ghia-jane* should be a new assignee for this issue.

1. Append
---------

Append strategy adds new assignees to the already existing assignees.

.. testcode::

   process_issue(issue, "append", rules)
   print("Assignees:", sorted(issue.assignees))

.. testoutput::

    Assignees: ['Codertocat', 'ghia-jane']

The user *ghia-jane* was added to the issue assignees.

.. testcode::
   :hide:

   issue.assignees = {'Codertocat'}

2. Set
------

Set strategy adds assignees only in case the issue was not assigned to anyone.

.. testcode::

   process_issue(issue, "set", rules)
   print("Assignees:", sorted(issue.assignees))

.. testoutput::

    Assignees: ['Codertocat']

The user *ghia-jane* was not added to the issue assignees, as the issue was
previously assigned to *Codertocat*.

3. Change
---------

Change strategy removes all existing assignees and assigns the issue to the
users matched by the rules.

.. testcode::

   process_issue(issue, "change", rules)
   print("Assignees:", sorted(issue.assignees))

.. testoutput::

    Assignees: ['ghia-jane']

The user *ghia-jane* is now the only assignee of the issue.
