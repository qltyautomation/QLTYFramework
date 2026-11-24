=============================
QLTY for mobile browsers
=============================
QLTY allows you to test responsive web platforms with a few tweaks.
This guide will walk you through the process of running tests on either chrome mobile or safari mobile


Command line platform option
===============================
When running your mobile browser tests you need to send either one of the following options for the platform:

:code:`--platform=android_web` or :code:`--platform=ios_web`

Running appium with chromedriver auto download
===============================================
Appium requires to have the proper version to automate the Chrome mobile browser that is installed on the device.
You can refer to the `Google chromedriver site <https://chromedriver.chromium.org/downloads>`_ to get the proper chromedriver

Another (easier) solution is to run appium with the following flag:

:code:`appium --allow-insecure chromedriver_autodownload`

This will allow the appium server to fetch the mobile chrome version and retrieve the proper chromedriver needed to automate
the mobile browser.


Code organization
====================
Your mobile web controllers need to exist in the following path: :code:`controllers/\web`

.. note::

    There is no differentiation in the controller for iOS or Android since the application is not native but a
    responsive web application

Mobile browser capabilities
==============================
Make sure you add a set of capabilities to your :code:`settings.py` file, the following example is for Chrome mobile.

Please refer to `Appium mobile browser capabilities <https://appium.io/docs/en/writing-running-appium/web/mobile-web/>`_ for further information

.. code:: python

        'android_web': {
            'newCommandTimeout': 99999,
            'platformName': 'Android',
            'platformVersion': '12.0',
            'deviceName': 'Android Emulator',
            'automationName': 'UIAutomator2',
            'browserName': 'Chrome'
        }
