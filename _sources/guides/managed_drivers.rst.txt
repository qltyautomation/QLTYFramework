=============================
Managed drivers
=============================
This section covers the usage of **managed drivers** which allows the user to instantiate an amount of drivers for whatever
platform is required.

A simple use case for this feature is as follows:
A test case requires you to create a new account through a native application (iOS or Android), after successful creation
the application requires you to verify a link that was sent to the users email address.
The user then needs to open either a desktop browser (chrome or firefox) or a mobile browser (mobile chrome, mobile firefox)
to click on the link and continue with the registration.

This is where **managed drivers** come in. To use this functionality you need to send the flag :code:`-d` or :code:`--managed` in
your command line arguments.

    .. warning::
        Setting this flag will make QLTY **not** create any drivers for your test run. Commonly, QLTY will create a driver for
        you for whatever platform you sent in your CLI arguments.
        This means that you are responsible for creating your drivers and setting the correct capabilities in your :code:`settings.py` file.


Tests organization
=====================

Usually QLTY uses the given platform to load the tests that are in this platform folder.
This is still the case for using **managed drivers** regardless of whether the test case starts or ends in the given platform.

A recommendation would be to place your tests on the directory for the platform where the majority of the test case takes place.
In the given example, most of the registration happens in the native side (iOS or Android) so it would make sense to place them
in the iOS or Android test directory.

Creating a new driver
=======================
As mentioned before with this feature you are now responsible of creating your own webdriver.
Make sure that the proper capabilities for the drivers that you are going to be using are set up in your :code:`settings.py` file.

    .. note::
        When running your tests on SauceLabs, creating a native driver will automatically request the device to Saucelabs.
        There is no support for creating native drivers both locally and in saucelabs at the same time.

To create a new driver:

    .. code-block:: python

        android_driver = initialize_driver(self, 'android')

The current available platforms to create a new driver are: :code:`android`, :code:`ios`, :code:`android_web`, :code:`ios_web`,
:code:`chrome` and :code:`firefox`.

    .. warning::
        When running your tests on `Saucelabs` note that sessions will be automatically terminated if they have not received
        a command in 90 seconds. It is recommended that you create your driver when you are about to use it. If you create
        all your drivers at the beginning of the test case chances are that the first drivers will be terminated by the
        time you need them.

Instantiating your controllers
================================
In the code above you can notice that we kept a reference to the driver that we just created. This is required since we need
to create our controllers and pass that driver.

When running QLTY without the **managed drivers** feature, you would usually instantiate your controllers in the :code:`setUp()`
method of your test class. This is possible due to the fact that at that point you already have a reference to the driver and
the test case will only use a single driver for the entire test execution.

With **managed drivers** we can no longer do that in the :code:`setUp()` method since QLTY does not know which drivers are going
to be initialized nor which controllers are needed.

That is why you need to register your controllers **after** you created your driver:

    .. code-block:: python

        android_driver = initialize_driver(self, 'android')
        self.controllers.register_controller('homepage', HomepageController(android_driver)

You can now use your controllers and they will work on the driver that you used to register them.

Terminating your drivers
===========================
There is no need to terminate your drivers at the end of your test execution.
QLTY registers every new driver to the current test case and when the test case is completed it will fetch the logs for whatever
platform the driver is for and call the :code:`tearDown` method which essentially closes the session.
