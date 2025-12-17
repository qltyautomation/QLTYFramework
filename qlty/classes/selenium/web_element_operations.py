# Third party libraries
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as conditions
# Project libraries
import settings
from qlty.classes.selenium.selenium_operations import SeleniumOperations
from qlty.utilities.utils import setup_logger

logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class WebElementOperations(SeleniumOperations):
    """
    Collection of utility methods for simplified web element interactions.
    Reduces boilerplate code when working with elements, eliminating the need for
    custom controller methods for common operations.
    """
    # Controller reference providing access to webdriver and locator definitions
    controller = None

    def __init__(self, controller, driver):
        """
        Initialize the operations helper
        """
        super(WebElementOperations, self).__init__(driver)
        self.controller = controller

    def op_click_element(self, locator_key):
        """
        Locates and clicks the element identified by locator_key

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :return:
        """
        try:
            # Verify element is ready for interaction
            WebDriverWait(self.driver, settings.SELENIUM['TIMEOUT'],
                          ignored_exceptions=StaleElementReferenceException).until(
                conditions.element_to_be_clickable(self.controller.LOCATORS[locator_key]),
                message='Element never became clickable:\nStrategy:{}\nSelector:{}'.format(
                    self.controller.LOCATORS[locator_key][0], self.controller.LOCATORS[locator_key][1]))
            logger.debug('Element [{}] is ready for interaction, performing click'.format(
                self.controller.LOCATORS[locator_key][1]))
            self.controller.get_element(self.controller.LOCATORS[locator_key]).click()
        except StaleElementReferenceException:
            # Element may have changed between retrieval and click, re-fetch and retry
            logger.debug('Stale element detected during click, re-fetching element')
            self.controller.get_element(self.controller.LOCATORS[locator_key]).click()

    def op_get_element_text(self, locator_key):
        """
        Retrieves the text content from the element identified by locator_key

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :return: Text content of the element
        :rtype: str
        """
        return self.controller.get_element(self.controller.LOCATORS[locator_key]).text

    def op_get_element_enabled(self, locator_key):
        """
        Checks whether the element identified by locator_key is currently enabled

        :param locator_key: Dictionary key for the locators collection
        :return: True when element is enabled, False otherwise
        :rtype: bool
        """
        return self.controller.get_element(self.controller.LOCATORS[locator_key]).is_enabled()

    def op_get_element_visibility(self, locator_key):
        """
        Checks whether the element identified by locator_key is currently visible

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :return: True when element is visible, False otherwise
        :rtype: bool
        """
        return self.controller.get_element(self.controller.LOCATORS[locator_key]).is_displayed()

    def op_get_element(self, locator_key, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Locates and returns the element identified by locator_key

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param timeout: Maximum wait time in seconds before raising an exception, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        :return: Located web element
        :rtype: WebElement
        """
        return self.controller.get_element(self.controller.LOCATORS[locator_key], timeout)

    def op_get_elements(self, locator_key):
        """
        Locates and returns all elements matching the specified locator_key

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :return: Collection of matching web elements
        :rtype: list
        """
        return self.controller.get_elements(self.controller.LOCATORS[locator_key])

    def op_get_element_value(self, locator_key):
        """
        Extracts the value attribute from the element identified by locator_key

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :return: Value attribute of the element
        :rtype: str
        """
        return self.controller.get_element(self.controller.LOCATORS[locator_key]).get_attribute('value')

    def op_wait_for_text_in_elements(self, locator_key, text):
        """
        Waits until elements matching the locator contain the specified text

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param text: Text content to wait for
        :type text: str
        """
        return self.controller.wait_for_text_in_elements(self.controller.LOCATORS[locator_key], text)

    def op_wait_for_element_to_not_be_visible(self, locator_key, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Waits until the element is no longer visible in the viewport

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        """
        return self.controller.wait_for_element_to_not_be_visible(self.controller.LOCATORS[locator_key], timeout)

    def op_browser_tap(self, locator_key, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Performs a tap action on the element (browser-specific implementation)

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        """
        return self.controller.browser_tap(self.controller.LOCATORS[locator_key], timeout)

    def op_swipe_until_visible(self, locator_key, attempts=3):
        """
        Repeatedly swipes until the target element becomes visible.
        Does not include implicit wait, assumes element is already loaded but not in viewport.

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param attempts: Maximum number of swipe-and-check cycles to perform
        :type attempts: int
        :return: Located web element
        :rtype: WebElement
        """
        return self.controller.swipe_until_visible(self.controller.LOCATORS[locator_key], attempts)

    def op_scroll_to_element(self, locator_key, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Scrolls the page until the element identified by locator_key is visible in the viewport.
        Uses JavaScript scrollIntoView for desktop web browsers.

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param timeout: Maximum wait time in seconds to find the element, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        :return: Located web element after scrolling
        :rtype: WebElement
        """
        element = self.controller.get_element(self.controller.LOCATORS[locator_key], timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        return element
