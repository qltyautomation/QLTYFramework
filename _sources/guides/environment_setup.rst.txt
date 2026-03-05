========================
Environment setup
========================
This section will guide you through the process of setting up your machine for local development

Quick Start (Automated Installation)
======================================
The easiest way to get started is using the automated installation script. This will set up your entire environment automatically.

**One-line installation:**

.. code-block:: bash

    curl -fsSL https://raw.githubusercontent.com/qltyautomation/QLTYFramework/main/install.sh | bash -s -- --repo YOUR_TEST_REPO_URL

Replace ``YOUR_TEST_REPO_URL`` with your test repository URL (e.g., ``https://github.com/yourorg/yourproject.git``)

**What the script does:**

- Installs Python 3 and Node.js (if not already installed)
- Sets up virtualenv and virtualenvwrapper
- Creates and activates a virtual environment
- Clones your test repository
- Installs all dependencies (QLTY Framework + requirements)
- Configures your environment

**Local installation script:**

If your test repository already has an ``install.sh`` file, you can run it directly:

.. code-block:: bash

    cd /path/to/your/test/repo
    chmod +x install.sh
    ./install.sh

.. note::

    After installation, you'll need to configure your ``local_settings.py`` file with your API keys and credentials.
    See the ``SETUP.md`` file in your test repository for details.

Manual Installation
=====================
If you prefer to set up your environment manually, follow these steps:

#. Install python 3 through homebrew
    .. code-block:: bash

        brew install python3

    It is recommended to use homebrew as it will create the required system links too

#. Install node through homebrew
    .. code-block:: bash

        brew install node

#. Install python virtual environment manager
    .. code-block:: bash

        pip3 install virtualenv

    Virtual environment manager helps us separate python installations and their dependencies

#. Install python virtual environment wrapper
    .. code-block:: bash

        pip3 install virtualenvwrapper

#. Add virtual environment configuration variables
    Edit your :code:`.bash_profile` or :code:`.zshrc` depending on which terminal you use and add
    the following environment variables:

    .. code-block:: bash

         export WORKON_HOME=~/.virtualenvs
         export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
         source /usr/local/bin/virtualenvwrapper.sh

#. Reopen your terminal or recompile your bash profile
    .. code-block:: bash

        source ~/.zshrc

#. Create a virtual environment for the project
    .. code-block:: bash

        mkvirtualenv qlty-myproject --python=python3

#. Activate your virtual environment
    .. code-block:: bash

        workon qlty-myproject

    Make sure that you always work on your virtual environment

#. Clone your test repository
    .. code-block:: bash

        git clone YOUR_TEST_REPO_URL
        cd YOUR_TEST_REPO

#. From the root directory of your test repo, install the requirements
    .. code-block:: bash

        pip3 install -r requirements.txt

    .. warning::

        You need to have your SSH keys added to your GitHub account if using SSH URLs.
        Please follow `this guide <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent>`_ on how to add your SSH keys to your GitHub account

#. Configure your local settings
    .. code-block:: bash

        cp local_settings.py.example local_settings.py

    Then edit ``local_settings.py`` and add your API keys and credentials

#. Install Appium with node package manager
    .. code-block:: bash

        npm install -g appium

Appium installation
=====================
Please refer to `Appium - Getting started <http://appium.io/docs/en/2.0/quickstart/install/>`_ for the latest version on how to install and setup your machine for Appium
If you want to validate your installation you can use :code:`appium-doctor` as shown here :ref:`Appium doctor`.

Android studio installation
=============================
You will require a working installation of Android studio in order to use android emulators and real devices.

You can get the latest `android studio <https://developer.android.com/studio>`_ version here.

Xcode installation
====================
If you are going to work with iOS simulators, real devices or safari mobile you need to install Xcode on you machine.

Xcode gets installed through the Mac App store, `here <https://developer.apple.com/xcode/>`_ is the link.