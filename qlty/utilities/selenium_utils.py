# Native libraries
import os
# Third party libraries
from appium import webdriver
from selenium import webdriver as desktop_webdriver
from selenium.webdriver import ActionChains
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.support.ui import WebDriverWait
from appium.options.common import AppiumOptions
# Project libraries
import settings
import qlty.config as config
from qlty.utilities.utils import setup_logger
from qlty.classes.integrations.saucelabs_integration import SaucelabsHelper
from qlty.utilities.utils import is_browser_run

# Configure logging instance
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


def wait_for_web_context(driver, webview_name):
    """
    Waits until specified web view becomes available and switches context to it

    :param driver: Active driver instance
    :type driver: WebDriver
    :param webview_name: Target webview identifier
    :type webview_name: str
    """
    logger.debug('Awaiting available web context')
    # Wait for WEBVIEW context with specified name to become available
    WebDriverWait(driver, settings.SELENIUM['TIMEOUT']).until(
        lambda x: len([context for context in driver.contexts if webview_name in context]) > 0,
        message='Web context with qualified app name [{}] never became available'.format(webview_name))
    web_context = ''
    for c in driver.contexts:
        if webview_name in c:
            web_context = c
    if web_context == '':
        logger.error('Failed to retrieve web context, available contexts:\n{}'.format(driver.contexts))
    else:
        logger.debug('Switching to context: {}'.format(web_context))

    driver.switch_to.context(web_context)


def switch_to_native_context(driver):
    """
    Returns to native app context from web view

    :param driver: Active driver instance
    :type driver: `WebDriver`
    :return: None
    """
    logger.debug('Reverting to NATIVE context')
    driver.switch_to.context('NATIVE_APP')


def initialize_driver(test_case, platform, force_driver_creation=True):
    """
    Initializes appropriate driver based on platform and configuration

    :param test_case: A QLTY test case for retrieving class and method names
    :type: QLTYTestcase
    :param platform: Platform identifier string for webdriver selection
    :type: String
    :param force_driver_creation: Override configuration to force driver initialization
    """
    # Handle managed driver mode
    if config.MANAGED_DRIVERS and not force_driver_creation:
        logger.info('Test execution using managed drivers, skipping default web driver initialization')
        return None

    driver = None
    # Configure Saucelabs remote driver if integration enabled
    if config.SAUCELABS_INTEGRATION and not is_browser_run(platform):
        driver = SaucelabsHelper.get_saucelabs_appium_remote(test_case, platform)
    else:
        # Initialize local webdriver instance
        if config.DESKTOP_BROWSER:
            driver = get_desktop_webdriver()
        else:
            # Retrieve platform-specific capabilities
            capabilities = settings.SELENIUM['CAPABILITIES'][platform]
            appium_remote = settings.SELENIUM['APPIUM']['URL']
            driver = webdriver.Remote(appium_remote, options=AppiumOptions().load_capabilities(capabilities))

    if driver is not None:
        # Register driver with test case
        logger.debug('Registering single driver with test case: session_id[{}]'.format(driver.session_id))
        test_case.drivers.append(driver)
        return driver


def get_desktop_webdriver():
    """
    Creates desktop browser webdriver instance from drivers directory
    """
    if config.CURRENT_PLATFORM == 'chrome':
        # Set up service (path to your chromedriver)
        service = Service("drivers/chromedriver")
        # Set up Chrome options
        options = Options()
        if config.HEADLESS:
            logger.info('Running Chrome in headless mode')
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
        return webdriver.Chrome(service=service, options=options)
    elif config.CURRENT_PLATFORM == 'firefox':
        return desktop_webdriver.Firefox()
    else:
        raise RuntimeError('Only Chrome desktop driver is currently supported')


def perform_tap_back(driver):
    """
    Executes back navigation action
    """
    if config.CURRENT_PLATFORM == 'ios':
        actions = ActionChains(driver)
        actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.w3c_actions.pointer_action.move_to_location(0, 0)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.release()
        actions.perform()
    else:
        driver.back()


def perform_tap_location(driver, offset):
    """
    Executes tap gesture using percentage-based coordinates

    :param driver: Active driver instance
    :type driver: WebDriver
    :param offset: Coordinate dictionary with offset_x and offset_y percentages
    :type offset: dict
    """
    tap_x = (offset['offset_x'] * driver.get_window_size()['width'])
    tap_y = (offset['offset_y'] * driver.get_window_size()['height'])
    perform_tap_based_on_cords(driver, {'x': tap_x, 'y': tap_y})


def perform_tap_based_on_cords(driver, coords):
    """
    Executes tap gesture using absolute viewport coordinates
    """
    x = coords['x']
    y = coords['y']
    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    actions.w3c_actions.pointer_action.move_to_location(x, y)
    actions.w3c_actions.pointer_action.pointer_down()
    actions.w3c_actions.pointer_action.release()
    actions.perform()


def perform_action_on_picker_wheel(driver, web_element, direction):
    """
    Manipulates iOS picker wheel element

    :param driver: Active driver instance
    :type driver: WebDriver
    :param web_element: Target web element
    :type web_element: WebElement
    :param direction: Navigation direction: :code:`Next` or :code:`Previous`
    :type direction: str
    """
    param = {
        'order': direction,
        'element': web_element
    }
    driver.execute_script('mobile: selectPickerWheelValue', param)
