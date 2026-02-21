# Third party libraries
from selenium.common.exceptions import (
    StaleElementReferenceException, NoSuchElementException, ElementClickInterceptedException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as conditions
# Project libraries
import settings
from qlty import config
from qlty.classes.selenium.selenium_operations import SeleniumOperations
from qlty.utilities.utils import setup_logger, is_browser_run

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

    def op_click_element(self, locator_key, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Locates and clicks the element identified by locator_key

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param timeout: Maximum wait time in seconds before raising an exception, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        :return:
        """
        try:
            # Verify element is ready for interaction
            WebDriverWait(self.driver, timeout,
                          ignored_exceptions=StaleElementReferenceException).until(
                conditions.element_to_be_clickable(self.controller.LOCATORS[locator_key]),
                message='Element never became clickable:\nStrategy:{}\nSelector:{}'.format(
                    self.controller.LOCATORS[locator_key][0], self.controller.LOCATORS[locator_key][1]))
            logger.debug('Element [{}] is ready for interaction, performing click'.format(
                self.controller.LOCATORS[locator_key][1]))
            element = self.controller.get_element(self.controller.LOCATORS[locator_key])
            self._scroll_into_view(element)
            element.click()
        except StaleElementReferenceException:
            # Element may have changed between retrieval and click, re-fetch and retry
            logger.debug('Stale element detected during click, re-fetching element')
            element = self.controller.get_element(self.controller.LOCATORS[locator_key])
            self._scroll_into_view(element)
            element.click()
        except ElementClickInterceptedException:
            # Element is obscured by another element, fall back to JS click
            logger.debug('Click intercepted on [{}], falling back to JavaScript click'.format(
                self.controller.LOCATORS[locator_key][1]))
            element = self.controller.get_element(self.controller.LOCATORS[locator_key])
            self._scroll_into_view(element)
            self.driver.execute_script("arguments[0].click();", element)

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

    def _scroll_into_view(self, element):
        """
        Scrolls an element into the visible center of the viewport.
        Only applies on desktop web platforms (Chrome/Firefox).

        :param element: WebElement to scroll into view
        :type element: WebElement
        """
        if is_browser_run(config.CURRENT_PLATFORM):
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                element
            )

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
        self._scroll_into_view(element)
        return element

    def op_select_dropdown_by_text(self, locator_key, text, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Selects an option from a dropdown (select element) by visible text.

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param text: Visible text of the option to select
        :type text: str
        :param timeout: Maximum wait time in seconds to find the element, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        """
        dropdown_element = self.controller.get_element(self.controller.LOCATORS[locator_key], timeout)
        self._scroll_into_view(dropdown_element)
        self._wait_for_dropdown_option(dropdown_element, 'text', text, timeout)
        select = Select(dropdown_element)
        select.select_by_visible_text(text)

    def op_select_dropdown_by_value(self, locator_key, value, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Selects an option from a dropdown (select element) by value attribute.

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param value: Value attribute of the option to select
        :type value: str
        :param timeout: Maximum wait time in seconds to find the element, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        """
        dropdown_element = self.controller.get_element(self.controller.LOCATORS[locator_key], timeout)
        self._scroll_into_view(dropdown_element)
        self._wait_for_dropdown_option(dropdown_element, 'value', value, timeout)
        select = Select(dropdown_element)
        select.select_by_value(value)

    def op_get_selected_dropdown_text(self, locator_key, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Gets the visible text of the currently selected option in a dropdown.

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param timeout: Maximum wait time in seconds to find the element, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        :return: Visible text of the selected option
        :rtype: str
        """
        dropdown_element = self.controller.get_element(self.controller.LOCATORS[locator_key], timeout)
        select = Select(dropdown_element)
        return select.first_selected_option.text

    def op_set_checkbox(self, locator_key, checked=True, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Sets a checkbox to checked or unchecked state.

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param checked: Desired state - True for checked, False for unchecked
        :type checked: bool
        :param timeout: Maximum wait time in seconds to find the element, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        """
        checkbox = self.controller.get_element(self.controller.LOCATORS[locator_key], timeout)
        if checked != checkbox.is_selected():
            self.op_click_element(locator_key, timeout)

    def op_is_checkbox_checked(self, locator_key, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Checks whether a checkbox is currently checked.

        :param locator_key: Dictionary key for the locators collection
        :type locator_key: str
        :param timeout: Maximum wait time in seconds to find the element, defaults to
            settings.SELENIUM['TIMEOUT'] from settings.py
        :type timeout: int
        :return: True if checkbox is checked, False otherwise
        :rtype: bool
        """
        checkbox = self.controller.get_element(self.controller.LOCATORS[locator_key], timeout)
        return checkbox.is_selected()

    def _wait_for_dropdown_option(self, dropdown_element, match_by, match_value, timeout):
        """
        Waits until a specific option is present inside a <select> element.
        Handles dropdowns whose options are populated asynchronously.

        :param dropdown_element: The <select> WebElement
        :param match_by: 'text' to match by visible text, 'value' to match by value attribute
        :param match_value: The text or value to look for
        :param timeout: Maximum wait time in seconds
        """
        def option_present():
            try:
                if match_by == 'text':
                    xpath = f".//option[normalize-space(.)='{match_value}']"
                else:
                    xpath = f".//option[@value='{match_value}']"
                dropdown_element.find_element(By.XPATH, xpath)
                return True
            except NoSuchElementException:
                return False

        self.wait_for(option_present, True, timeout=timeout)
