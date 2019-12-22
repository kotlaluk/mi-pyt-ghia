GHIA - GitHub Issue Assigner
============================

GHIA is a command-line and web application for automatic assignment of GitHub
issues based on their content. It utilizes GitHub API and supports GitHub
webhooks.

Features
--------

- Process GitHub issues in batches via CLI interface
- Process multiple GitHub repositories asynchronously
- Recieve GitHub webhooks via web application
- Define rules based on issue title, content, or label

Installation
------------

The project can be installed using pip from TestPyPI::

    pip install --extra-index-url https://test.pypi.org/pypi ghia-kotlaluk

Or by cloning GitHub repository::

    git clone https://github.com/kotlaluk/mi-pyt-ghia

and running::

    python setup.py install

Usage
-----

The CLI application can be invoked by running ``ghia``.
To view help run::

    ghia --help

To run the web application::

    export FLASK_APP=ghia
    export GHIA_CONFIG=config.cfg
    flask run

Follow the documentation for description of the format of configuration files.

Testing
-------

The project contains two different sets of tests:

- unit tests
- integration tests

Unit tests
~~~~~~~~~~

Unit tests are located in the ``tests`` folder and can be invoked by::

    python setup.py test

By default, unit tests do not require any environment variables to be set and
can be used offline, as they contain pre-recorded betamax cassettes.

To re-record the cassettes, set following environment variables::

    export GITHUB_TOKEN=<valid GitHub token>
    export BETAMAX_RECORD=1

and run::

    python setup.py test

Integration tests
~~~~~~~~~~~~~~~~~

Integration tests test behavior of the application towards running GitHub API
and check the correctness of the module.

To invoke these tests, set following environment variables:

- ``GITHUB_USER`` - GitHub username
- ``GITHUB_TOKEN`` - GitHub access token
- ``CTU_USERNAME`` - CTU username
- ``GHIA_REPO`` - path to the GHIA repository
  (e.g. https://github.com/kotlaluk/mi-pyt-ghia.git)

prepare the environment::

    cd original_tests/environment_setup
    bash delete.sh
    bash setup.sh
    cd -

and run following pytest command::

    python -m pytest original_tests/

Documentation
-------------

Documentation of the project is available at
`Read the Docs <https://ghia-kotlaluk.readthedocs.io>`_.

To build the documentation manually::

   cd docs
   make html

and open the file ``docs/_build/html/index.html`` in a web browser.

Author
------

Lukáš Kotlaba (lukas.kotlaba@gmail.com)

License
-------

The project is licensed under GNU General Public License v3.0.
