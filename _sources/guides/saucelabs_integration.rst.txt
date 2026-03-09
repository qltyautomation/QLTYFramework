=============================
Saucelabs integration
=============================
This section will explain how to run your tests on mobile devices in Saucelabs, you can either use emulators/simulators
or real devices.
The integration works by using a special set of capabilities that you need to define in your :code:`settings.py` file

Configuration
=================
You will need to set up the following values in your verticals repository :code:`settings.py` file:

    .. code-block:: python

        SAUCELABS = {
            'USERNAME': 'verticals',
            'ACCESS_KEY': '--REDACTED--',
            'URL': 'ondemand.us-west-1.saucelabs.com:443/wd/hub',
        }

:code:`USERNAME` is your login username to connect to saucelabs

:code:`ACCESS_KEY` is a unique token that authorizes you to connect to the saucelabs servers, this token can be
retrieved in your `user settings <https://app.saucelabs.com/user-settings>`_.

:code:`URL` refers to the location of the appium server running on saucelabs that you will connect, this value is also
retrieved from your `user settings <https://app.saucelabs.com/user-settings>`_. under the :code:`Ondemand URL` value.

Special capabilities
======================
A new set of capabilities needs to be added to your :code:`SELENIUM.CAPABILITIES` dictionary in your :code:`settings.py` file.
There are 4 different entries that you can add:

    #. :code:`android_saucelabs` refers to capabilities to run android tests on saucelabs

    #. :code:`ios_saucelabs` for iOS tests on saucelabs

    #. :code:`android_web_saucelabs` for android mobile (chrome) tests on saucelabs

    #. :code:`ios_web_saucelabs` for iOS mobile (safari) tests on saucelabs

The following is an example for :code:`android_saucelabs`:

    .. code-block:: python

        'android_web_saucelabs': {
                'platformName': 'Android',
                'browserName': 'Chrome',
                'appium:platformVersion': '12',
                'appium:automationName': 'UiAutomator2',
                'deviceOrientation': 'portrait',
            }

For more information on how to set up your capabilities please refer to the `saucelabs documentation <https://docs.saucelabs.com/overview/>`_

Tunneling
==============
Saucelabs provides a way to connect through their services and bypass internal security systems. This is required to access
resources protected by Salesforce VPN while running on saucelabs.
To set a tunnel to connect to saucelabs while running locally please download the latest binaries for your platform
from `here <https://docs.saucelabs.com/secure-connections/sauce-connect/installation/>`_


