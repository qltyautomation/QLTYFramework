# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
from unittest.mock import MagicMock

# Add the project directory structure to sys path so that autodoc may import relevant modules
sys.path.append(os.path.abspath('../qlty'))
sys.path.append(os.path.abspath('../qlty/classes'))
sys.path.append(os.path.abspath('../qlty/classes/api'))
sys.path.append(os.path.abspath('../qlty/classes/integrations'))
sys.path.append(os.path.abspath('../qlty/classes/selenium'))
sys.path.append(os.path.abspath('../qlty/classes/core'))
sys.path.append(os.path.abspath('../qlty/classes/controllers/android'))
sys.path.append(os.path.abspath('../qlty/utilities'))
sys.path.append(os.path.abspath('../'))

# Mock these modules so they don't need to be imported for the purposes of autodoc
autodoc_mock_imports = ["settings", "local_settings", "appium", "selenium",
                        "unittest2", "numpy", "slack_sdk", "boto3", "botocore", "requests"]
autodoc_typehints = 'description'
autodoc_member_order = 'alphabetical'
# Set the debug level of the mock settings module
settings_mock = MagicMock()
settings_mock.DEBUG_LEVEL = 1
sys.modules['settings'] = settings_mock
# -- Project details configuration -------------------------------------------
project = 'QLTY Framework'
copyright = '2024, QLTY Automation'
author = 'Eduardo Reynoso | QLTY Automation'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Enable extensions for autodoc and including comments from source files
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.githubpages',
              ]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'display_version': True,
    'style_nav_header_background': '#131927',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Custom CSS files
html_static_path = ['_static']
html_css_files = [
    'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap',
    'custom.css',
]

# Logo configuration
html_logo = '_static/qltyautomationlogo.jpg'
html_favicon = '_static/qltyautomationlogo.jpg'