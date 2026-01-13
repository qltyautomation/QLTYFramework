# Native libraries
import time
# Third party libraries
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as conditions
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.by import By
import numpy
# Project libraries
import settings
import qlty.config as config
from qlty.utilities.utils import setup_logger
from qlty.utilities.utils import ANDROID_SWIPE_OFFSETS

logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class SeleniumOperations:
    #: Driver reference for web automation
    driver = None

    def __init__(self, driver):
        """
        Initialize the class with a webdriver instance

        :param driver: Selenium WebDriver instance
        :type driver: WebDriver
        """
        self.driver = driver

    def get_element(self, locator, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Locates and returns a web element after confirming its presence in the DOM

        :param locator: Tuple containing locator strategy and value, for example:

            .. code-block:: python

                (By.XPATH, '//android.widget.Button[@resource-id="oaapprove"]')

        :type locator: tuple
        :param timeout: Maximum wait time in seconds before raising an exception, defaults to :code:`settings.SELENIUM['TIMEOUT']`
        :type timeout: int
        :return: Located web element
        :rtype: WebElement
        """
        WebDriverWait(self.driver, timeout,
                      ignored_exceptions=StaleElementReferenceException).until(
            conditions.presence_of_element_located([locator[0], locator[1]]),
            message='Element could not be found using the specified criteria:\nStrategy:{}\nSelector:{}'.format(
                locator[0], locator[1]))
        return self.driver.find_element(locator[0], locator[1])

    def get_elements(self, locator):
        """
        Locates and returns multiple web elements that match the specified criteria. Waits until at least one element
        is found in the DOM.

        :param locator: Tuple containing locator strategy and value, for example:

            .. code-block:: python

                (By.XPATH, '//android.widget.Button[@resource-id="oaapprove"]')

        :type locator: tuple
        :return: Collection of matching web elements
        :rtype: list
        """
        WebDriverWait(self.driver, settings.SELENIUM['TIMEOUT']).until(
            conditions.presence_of_all_elements_located([locator[0], locator[1]]),
            message='No matching elements found using the specified criteria:\nStrategy:{}\nSelector:{}'.format(
                locator[0], locator[1]))
        return self.driver.find_elements(locator[0], locator[1])

    def wait_for_text_in_elements(self, locator, text):
        """
        Waits until any element matching the locator contains the specified text content. Ignores stale element
        exceptions during the wait.

        :param locator: Tuple containing locator strategy and value, for example:

            .. code-block:: python

                (By.XPATH, '//android.widget.Button[@resource-id="oaapprove"]')

        :type locator: tuple
        :param text: Text content to search for within elements
        :type text: str
        :return: None
        """
        return WebDriverWait(
            self.driver, settings.SELENIUM['TIMEOUT'], ignored_exceptions=[StaleElementReferenceException]).until(
            lambda x: self._text_to_be_present_in_elements(locator, text),
            message="No elements contained the specified text:\n Strategy:{}\n Selector:{}\nExpected Text:{}".format(
                locator[0], locator[1], text))

    def wait_for_element_to_not_be_visible(self, locator, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Waits until the specified element is no longer visible in the viewport

        :param locator: Tuple containing locator strategy and value, for example:

            .. code-block:: python

                (By.XPATH, '//android.widget.Button[@resource-id="oaapprove"]')

        :type locator: tuple
        :param timeout: Maximum wait time in seconds before raising an exception, defaults to :code:`settings.SELENIUM['TIMEOUT']`
        :type timeout: int
        """
        WebDriverWait(self.driver, timeout).until(
            conditions.invisibility_of_element([locator[0], locator[1]]),
            message='Element remained visible:\nStrategy:{}\nSelector:{}'.format(locator[0], locator[1]))

    def _text_to_be_present_in_elements(self, locator, text):
        """
        Internal method that searches through elements until finding one containing the specified text

        :param locator: Tuple containing locator strategy and value, for example:

            .. code-block:: python

                (By.XPATH, '//android.widget.Button[@resource-id="oaapprove"]')

        :type locator: tuple
        :param text: Text content to search for within elements
        :type text: str
        """
        try:
            element_list = self.driver.find_elements(by=locator[0], value=locator[1])
            elements_text = [element.text for element in element_list]

            for i, element in enumerate(elements_text):
                if text in element:
                    return element_list[i]
        except StaleElementReferenceException:
            return False

    def try_fetch(self, function):
        """
        Attempts to execute the provided function for element retrieval. Specifically designed for element
        fetching operations, catching only :code:`NoSuchElementException`. Useful when checking for optional
        elements that may or may not exist. Does not include implicit wait behavior.
        All other exceptions will be raised normally.
        Provide a function reference as the parameter.
        """
        try:
            return function()
        except NoSuchElementException:
            logger.debug('try_fetch: Element was not found')
            return None

    def swipe(self, offset=None):
        """
        Executes a swipe gesture based on the provided offset parameters

        :param offset: Dictionary specifying swipe coordinates with start_x, start_y, end_x, end_y values
            expressed as percentages (0-1) of viewport dimensions. For instance, start_y of 0.25 begins
            the swipe at 25% of the viewport height
        :type offset: dict
        """
        if config.CURRENT_PLATFORM == 'ios':
            self._swipe_ios(offset)
        else:
            self._swipe_android(offset)
        # Wait for swipe animation to complete
        import time
        time.sleep(settings.SELENIUM['STEP_TIME'])

    def _swipe_android(self, offset):
        """
        Executes a swipe gesture for Android devices

        :param offset: Dictionary specifying swipe coordinates with start_x, start_y, end_x, end_y values
            expressed as percentages (0-1) of viewport dimensions. For instance, start_y of 0.25 begins
            the swipe at 25% of the viewport height
        :type offset: dict
        """
        # Calculate pixel boundaries for the viewport
        viewport = self.driver.get_window_size()
        min_height = 1
        max_height = viewport['height'] - 1
        min_width = 1
        max_width = viewport['width'] - 1

        # Constrain coordinates to ensure they remain within viewport bounds
        coordinates = {
            'start_x': int(numpy.clip(viewport['width'] * offset['start_x'], min_width, max_width)),
            'start_y': int(numpy.clip(viewport['height'] * offset['start_y'], min_height, max_height)),
            'end_x': int(numpy.clip(viewport['width'] * offset['end_x'], min_width, max_width)),
            'end_y': int(numpy.clip(viewport['height'] * offset['end_y'], min_height, max_height))
        }

        self.driver.swipe(coordinates['start_x'], coordinates['start_y'],
                          coordinates['end_x'], coordinates['end_y'])
        logger.debug('Executing swipe with coordinates {}'.format(coordinates))

    def _swipe_ios(self, offset):
        """
        Executes a swipe gesture for iOS devices

        :param offset: Dictionary specifying swipe coordinates with start_x, start_y, end_x, end_y values
            expressed as percentages (0-1) of viewport dimensions. For instance, start_y of 0.25 begins
            the swipe at 25% of the viewport height
        :type offset: dict
        """
        direction = offset['direction']
        self.driver.execute_script('mobile: swipe', {'direction': direction})
        # Allow animation to finish
        time.sleep(1)

    def wait_for(self, method, expected_result, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Continuously evaluates the provided method until its result matches the expected value.

        :param method: Function reference to evaluate
        :type method: func
        :param expected_result: Target value that the method should return, should be boolean-compatible
        :type expected_result: bool
        :param timeout: Maximum wait time in seconds for condition to be met
        :type timeout: Int
        :return:
        """
        return WebDriverWait(self.driver, timeout,
                             ignored_exceptions=StaleElementReferenceException).until(
            lambda x: method() == expected_result,
            message="Method result never matched the expected value")

    def switch_to_new_window(self, original_window):
        """
        Switches to a newly opened browser window/tab, excluding the original window.

        :param original_window: Handle of the original window to exclude from switching
        :type original_window: str
        :return: Handle of the new window that was switched to
        :rtype: str
        """
        for window_handle in self.driver.window_handles:
            if window_handle != original_window:
                self.driver.switch_to.window(window_handle)
                logger.debug(f'Switched to new window: {window_handle}')
                return window_handle
        raise RuntimeError('No new window found to switch to')

    def get_current_url(self):
        """
        Returns the current URL using JavaScript, which doesn't wait for page load.
        Useful when you need to check the URL of a slow-loading page immediately.

        :return: Current page URL
        :rtype: str
        """
        return self.driver.execute_script("return window.location.href;")

    def tap_element_at(self, web_element, x_offset, y_offset):
        """
        Performs a tap action at specific coordinates within an element's boundaries

        :param web_element: Target element for the tap action
        :type web_element: `WebElement`
        :param x_offset: Horizontal position within element, where 0 is left edge and 1 is right edge
        :type x_offset: int
        :param y_offset: Vertical position within element, where 0 is top edge and 1 is bottom edge
        :type y_offset: int
        """
        # Calculate relative coordinates for the tap action
        tap_x = x_offset * web_element.size['width']
        tap_y = y_offset * web_element.size['height']
        # Obtain element position coordinates
        raise NotImplementedError("This method requires updates for appium python client 3.0 compatibility")
        # TouchAction(self.driver).tap(element=web_element, x=tap_x, y=tap_y).perform()

    def drag_and_drop(self, source, target):
        """
        Executes a drag-and-drop operation by pressing the mouse button on the source element,
        moving to the target element, and releasing.

        :param source: Element where the drag begins.
        :type source: WebElement
        :param target: Element where the drop occurs.
        :type target: WebElement
        :return None:
        """
        raise NotImplementedError("This method requires updates for appium python client 3.0 compatibility")
        # touch_action = TouchAction(self.driver)
        # touch_action.press(source)
        # touch_action.move_to(target, None, None)
        # touch_action.release()
        # touch_action.perform()

    def drag_and_drop_by_offset(self, source, xoffset, yoffset):
        """
        Executes a drag-and-drop operation by pressing the mouse button on the source element,
        moving by the specified offset, and releasing.

        :param source: Element where the drag begins.
        :type source: `WebElement`
        :param xoffset: Horizontal distance to move.
        :type xoffset: Int
        :param yoffset: Vertical distance to move.
        :type yoffset: Int
        """
        raise NotImplementedError("This method requires updates for appium python client 3.0 compatibility")
        # source_loc = source.location
        # new_x = source_loc['x'] + xoffset
        # new_y = source_loc['y'] + yoffset
        # touch_action = TouchAction(self.driver)
        # touch_action.press(source)
        # touch_action.move_to(None, new_x, new_y)
        # touch_action.release()
        # touch_action.perform()

    def tap(self, locator):
        """
        Performs a reliable click operation on an element, retrying until successful.
        Uses WebDriverWait and handles `StaleElementReferenceException` and `NoSuchElementException`

        :param locator: Tuple containing locator strategy and value
        :type locator: tuple
        """
        WebDriverWait(self.driver, timeout=settings.SELENIUM['TIMEOUT'],
                      ignored_exceptions=[StaleElementReferenceException, NoSuchElementException]).until(
            lambda x: self._bool_click(self.get_element(locator)))

    def _bool_click(self, element):
        """
        Internal helper that attempts element click and returns success status

        :param element: Element to click
        :return: True if click succeeded, False otherwise
        :rtype: Boolean
        """
        try:
            element.click()
            return True
        except:
            return False

    def browser_tap(self, locator, timeout=settings.SELENIUM['TIMEOUT']):
        """
        Performs a tap action on an element in mobile browser context
        :param locator: Tuple containing By strategy and selector string, for example:

        .. code-block:: python

            (By.XPATH, '//android.widget.Button[@resource-id="oaapprove"]')

        :type locator: tuple
        :param timeout: Maximum wait time in seconds before raising an exception, defaults to :code:`settings.SELENIUM['TIMEOUT']`
        :type timeout: int
        """
        # Wait for element to become interactable
        WebDriverWait(self.driver, timeout,
                      ignored_exceptions=StaleElementReferenceException).until(
            conditions.element_to_be_clickable([locator[0], locator[1]]),
            message='Element never became clickable:\nStrategy:{}\nSelector:{}'.format(
                locator[0], locator[1]))

        if config.CURRENT_PLATFORM == 'ios_web':
            self.driver.execute_script("arguments[0].click();", self.get_element(locator, timeout))
        elif config.CURRENT_PLATFORM == 'android_web':
            self.get_element(locator, timeout).click()
        else:
            raise RuntimeError('Browser tap is only supported for mobile browser automation')

    def tap_android_button(self, button_text):
        """
        Clicks an Android button based on its text content
        Uses xpath expression: :code:`//android.widget.Button[@text="{BUTTON_TEXT}"]`
        Note: When multiple buttons share the same text, only the first match will be clicked

        :param button_text: Text displayed on the button
        """
        self.get_element((By.XPATH, '//android.widget.Button[@text="{}"]'.format(button_text))).click()

    def swipe_until_visible(self, locator, attempts=3):
        """
        Repeatedly swipes in the specified direction until the target element becomes visible.
        Does not include implicit wait, assumes element is already loaded but not in viewport.

        :param locator: Tuple containing locator strategy and selector
        :type locator: Tuple
        :param attempts: Maximum number of swipe-and-check cycles to perform
        :type attempts: int
        :return: Located web element
        :rtype: WebElement
        """
        while attempts > 0:
            try:
                element = self.driver.find_element(locator[0], locator[1])
                logger.debug('[{}][{}] Element located after swipe operation'.format(locator[0], locator[1]))
                return element
            except NoSuchElementException:
                logger.debug('Element not found, executing downward swipe')
                self.swipe(ANDROID_SWIPE_OFFSETS['down'])
                # Wait for swipe animation to complete
                time.sleep(settings.SELENIUM['STEP_TIME'])
            attempts -= 1
        raise NoSuchElementException('Element could not be found using locator {} '
                                     'after performing swipe operations'.format(locator))
