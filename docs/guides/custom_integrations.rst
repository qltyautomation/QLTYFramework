Creating Custom Integrations
=============================

QLTY Framework uses a lifecycle-based integration system. Integrations extend the
``Integration`` base class and override hooks that run at specific points during
test execution. A central registry dispatches lifecycle events to all enabled
integrations.

Lifecycle Hooks
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Hook
     - When it runs
   * - ``on_run_start()``
     - Before tests execute. Use for config validation and connection checks.
       If this raises an exception, the integration is deregistered and its
       other hooks will not be called. Tests still run.
   * - ``on_test_end(test_case, result)``
     - After each individual test completes.
   * - ``on_run_end(test_results, test_run_id, elapsed_time, log_path, context)``
     - After all tests complete. Use for reporting results to external systems.
       ``context`` is a shared dict that integrations can read from and write to.

Step-by-step
------------

1. **Create the integration class**

   Create a new file in ``qlty/classes/integrations/``:

   .. code-block:: python

      # qlty/classes/integrations/example_integration.py
      from qlty.classes.integrations.base_integration import Integration
      from qlty.utilities.utils import setup_logger
      import settings

      logger = setup_logger(__name__, settings.DEBUG_LEVEL)


      class ExampleIntegration(Integration):

          def __init__(self):
              self.api_key = settings.EXAMPLE['API_KEY']

          def on_run_start(self):
              """Validate credentials before tests run."""
              logger.info('Validating Example integration...')
              # Make a test API call, raise on failure
              ...

          def on_run_end(self, test_results, test_run_id, elapsed_time,
                         log_path=None, context=None):
              """Report results after tests complete."""
              from qlty.classes.core.test_runner_utils import TestRunnerUtils
              totals = TestRunnerUtils.get_testrun_totals(test_results)
              logger.info('Reporting {} results to Example'.format(
                  totals['total_testcases']))
              # Post results to external service
              ...

   Only override the hooks you need. The base class provides no-op defaults.

2. **Add a config flag**

   In ``qlty/config.py``:

   .. code-block:: python

      #: Enable Example integration
      EXAMPLE_INTEGRATION = False

3. **Add a CLI argument**

   In ``qlty/utilities/argument_parser.py``, add a new argument that sets the flag:

   .. code-block:: python

      parser.add_argument('-x', '--example',
                          action='store_true',
                          help='Enable Example integration')

   Then in the argument processing logic, set the config flag:

   .. code-block:: python

      if args.example:
          config.EXAMPLE_INTEGRATION = True

4. **Register the integration**

   In ``qlty/qlty_tests.py``, add to ``_register_integrations()``:

   .. code-block:: python

      if config.EXAMPLE_INTEGRATION:
          from qlty.classes.integrations.example_integration import ExampleIntegration
          registry.register(ExampleIntegration())

5. **Add settings**

   In the test project's ``settings.py``:

   .. code-block:: python

      EXAMPLE = {
          'API_KEY': os.getenv('EXAMPLE_API_KEY'),
      }

Sharing Data Between Integrations
----------------------------------

The ``context`` dict passed to ``on_run_end`` allows integrations to share data
without direct dependencies. For example, TestRail sets ``context['testrail_run_id']``
and Slack reads it to include a link in the notification.

.. code-block:: python

   # In a producer integration
   def on_run_end(self, test_results, test_run_id, elapsed_time,
                  log_path=None, context=None):
       run_id = self._create_run(...)
       if context is not None:
           context['my_run_id'] = run_id

   # In a consumer integration
   def on_run_end(self, test_results, test_run_id, elapsed_time,
                  log_path=None, context=None):
       run_id = context.get('my_run_id') if context else None
       # Use run_id if available, skip if not

Error Handling
--------------

- ``on_run_start``: If validation raises, the integration is **deregistered**.
  Tests proceed normally, and the integration's ``on_run_end`` is not called.
- ``on_run_end``: If one integration fails, the error is logged and the
  remaining integrations still run.
