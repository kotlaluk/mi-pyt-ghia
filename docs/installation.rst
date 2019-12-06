.. _installation-label:

Installation & Tests
====================

Installation
------------

GHIA can be installed using pip from TestPyPI::

    pip install --extra-index-url https://test.pypi.org/pypi ghia-kotlaluk

Or by cloning GitHub repository::

    git clone https://github.com/kotlaluk/mi-pyt-ghia

and running::

    python setup.py install

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
and validate the correctness of the module and packaging.

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
