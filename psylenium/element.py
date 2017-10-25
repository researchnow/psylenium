import time

from selenium.webdriver.remote.webdriver import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select

from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException, \
    StaleElementReferenceException

from .exceptions import DriverException, TimeOutException


def check_if_by_should_be_xpath(*, by: str, locator: str):
    """ Checks the given locator to see if it is an XPATH, and overrides the given 'by' argument if it is. """

    if by == By.CSS_SELECTOR:
        if locator.startswith("//") or locator.startswith("./") or "[contains(" in locator:
            return By.XPATH
    return by


def wait_for_element(*, driver, locator, by=By.CSS_SELECTOR, timeout=10, visible=True):
    """ Waits for a given element as defined by the 'by' and 'locator' arguments. Raises a TimeOutException instead of
     a TimeoutException in order to prevent the extra Selenium traceback. """

    by = check_if_by_should_be_xpath(by=by, locator=locator)
    try:
        if visible:
            WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, locator)))
        else:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, locator)))
    except TimeoutException:
        raise TimeOutException(by=by, locator=locator, timeout=timeout) from None
    except Exception as e:
        raise DriverException(e.__class__.__name__, str(e)) from None


def wait_until_not_visible(*, driver, locator, by=By.CSS_SELECTOR, timeout=10):
    """ Waits until the given element (as defined by the 'by' and 'locator' arguments) is no longer visible - i.e.
    loading icons, etc. """

    by = check_if_by_should_be_xpath(by=by, locator=locator)
    try:
        for _ in range(timeout):
            if not driver.find_element(by=by, value=locator).is_displayed():
                return True
            time.sleep(1)
    except (NoSuchElementException, StaleElementReferenceException, TimeoutException, AttributeError):
        return True
    raise Exception(f"Target element ({by} locator [ {locator} ]) still visible after wait period.")


# TODO: Review this; should it be checking displayed?
def element_exists(*, driver, locator, by=By.CSS_SELECTOR):
    """ Checks if an element exists for the given locator, and whether it's displayed"""
    by = check_if_by_should_be_xpath(by=by, locator=locator)
    for e in driver.find_elements(by=by, value=locator):
        if e.is_displayed():
            return True
    return False


class Element(object):
    """ A wrapper around the WebElement class, allowing us to make improvements as we see fit. While not a true child
    class, it has accessors for all attributes and methods in the WebElement class.

    :type _element: WebElement
    """
    def __init__(self, *, by: str, locator: str, web_element: WebElement, parent=None):
        self.by = by
        self.locator = locator
        self._element = web_element
        self._parent = parent

    def __repr__(self):
        return f"<Element object for {self.by} locator [ {self.locator} ]>"

    def __eq__(self, other):
        if isinstance(other, (str, int)):
            return self.text == str(other)
        return super().__eq__(other)

    @property
    def driver(self):
        return self._element.parent

    @property
    def parent(self):
        return self._parent or self.driver

    @property
    def tag_name(self):
        return self._element.tag_name

    @property
    def text(self):
        return self._element.text

    # Wrapper methods around the actual WebElement's methods, allowing us to access them without using _element and also
    # to modify them when we need to.
    def click(self, *, wait=True, timeout=10, offset=0, retry=True):
        try:
            if not wait:
                return self._element.click()

            clickable = WebDriverWait(self.parent, timeout).until(EC.element_to_be_clickable((self.by, self.locator)))
            if offset:
                ActionChains(self.driver).move_to_element_with_offset(clickable, 0, offset).click().perform()
            else:
                clickable.click()
        except WebDriverException as e:
            print(e)
            if "Other element would receive the click" in str(e) and retry:
                time.sleep(2)
                return self.click(wait=wait, timeout=timeout, offset=offset, retry=False)
            raise DriverException(e.__class__.__name__, str(e)) from None

    def submit(self):
        self._element.submit()

    def clear(self):
        self._element.clear()

    def get_property(self, name):
        return self._element.get_property(name)

    def get_attribute(self, name):
        return self._element.get_attribute(name)

    def is_selected(self):
        return self._element.is_selected()

    def is_enabled(self):
        return self._element.is_enabled()

    def send_keys(self, *value):
        self._element.send_keys(*value)

    def dropdown(self):
        return Select(self._element)

    def is_displayed(self):
        return self._element.is_displayed()

    def value_of_css_property(self, property_name):
        return self._element.value_of_css_property(property_name)

    @property
    def value(self):
        return self._element.get_attribute('value')

    @property
    def location(self):
        return self._element.location

    def find_element(self, value: str, *, by=By.CSS_SELECTOR):
        """ Wrapper around the WebElement's find_element that will return an Element instead of a WebElement. Also
        catches any Selenium errors and raises them without the excess traceback. """

        by = check_if_by_should_be_xpath(by=by, locator=value)
        try:
            new_element = self._element.find_element(by=by, value=value)
        except Exception as e:
            raise DriverException(e.__class__.__name__, str(e)) from None
        return Element(by=by, locator=value, web_element=new_element, parent=self._element)

    def find_elements(self, value: str, *, by=By.CSS_SELECTOR):
        by = check_if_by_should_be_xpath(by=by, locator=value)
        new_elements = self._element.find_elements(by=by, value=value)
        return [Element(by=by, locator=value, web_element=e, parent=self._element) for e in new_elements]

    # Other methods
    def set_value(self, text, *, tab=False):
        self.click()
        self.clear()
        self.send_keys(text)
        if tab:
            self.send_keys(Keys.TAB)

    def hover(self):
        hover = ActionChains(self.driver).move_to_element(self._element)
        hover.perform()

    def double_click(self):
        chain = ActionChains(self.driver).double_click(self._element)
        chain.perform()

    def highlight(self):
        """ Highlights (blinks) a Selenium WebDriver element. """

        def apply_style(s):
            self.driver.execute_script("arguments[0].setAttribute('style', arguments[1]);", self._element, s)

        original_style = self._element.get_attribute('style')
        apply_style("background: yellow; border: 2px solid red;")
        time.sleep(.3)
        apply_style(original_style)

    def scroll_to(self):
        """ Scrolls to an element. """
        self.driver.execute_script("arguments[0].scrollIntoView()", self._element)


class SelectElement(Element):
    """ An extension of the Element class that replicates the Select class from Selenium. """

    def __init__(self, normal_element: Element):
        super().__init__(by=normal_element.by, locator=normal_element.locator, web_element=normal_element._element)
        self._select = Select(self._element)

    def select_text(self, text):
        return self._select.select_by_visible_text(text)

    def select_by_index(self, index):
        return self._select.select_by_index(index)

    def select_value(self, val):
        return self._select.select_by_value(val)
