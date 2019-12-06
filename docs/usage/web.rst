.. _web-label:

WEB Application
===============

GHIA WEB processes GitHub isses in real-time. Once it receives a GitHub webhook
event containing information that an issue was created or changed, it will
assign users to the issue according to the loaded configuration.

The web application requires two environment variables to be set up.

- **FLASK_APP** needs to be set to ``ghia``
- **GHIA_CONFIG** needs to contain paths to one or more configuration files,
  separated by semicolon (:). At least one of the files should specify
  authentication infomration and at least one file should specify the matching
  rules. See the section :ref:`files-label` for the detais regarding the format
  of these files.

The web application can be started by running following commands:

.. code-block:: console

   export FLASK_APP=ghia
   export GHIA_CONFIG=auth.cfg:rules.cfg
   flask run

Once the web application is started, it will respond to a GET request on the
address ``/``. The response will contain a static HTML webpage displaying
information about the currently loaded configuration.

The application will also respond to POST requests on the address ``/``.
These POST requests must be GitHub webhooks *issues* or *ping*. The strategy
used for processing the issues is **append**.

`GitHub webhooks <https://developer.github.com/webhooks/>`_ allow the GHIA web
application to subscribe to specific events that can trigger on a GitHub
repository. GHIA web app listens to *issues* webhook - it reacts whenever
an issue is opened, edited, transferred, reopened, assigned, unassigned,
labeled, or unlabeled. To enable its functionality, it is necessary to set up
a webhook for *issues* event in JSON format on a GitHub repository, and bind it
to an URL of running GHIA web application, as described
`here <https://developer.github.com/webhooks/creating/>`_.

Optionally, GitHub webhooks can be
`secured <https://developer.github.com/webhooks/securing/>`_. GHIA web has
support for secured webhooks. If the webhooks are secured by using a secret
token, this token has to be a part of file containing authorization
configuration. See the section :ref:`files-label` for the detais regarding
the format of this file.
