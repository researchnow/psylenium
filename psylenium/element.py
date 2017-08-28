import time

from selenium.webdriver.remote.webdriver import WebElement as RemoteWebElement
from selenium.webdriver.common.by import By

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select

from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException, \
    StaleElementReferenceException
from .exceptions import DriverException, TimeOutException


def check_xpath_by(*, by, locator):
    if by == By.CSS_SELECTOR:
        if locator.startswith("//") or locator.startswith("./") or "[contains(" in locator:
            return By.XPATH
    return by


def wait_for_element(*, driver, locator, by=By.CSS_SELECTOR, timeout=10):
    by = check_xpath_by(by=by, locator=locator)
    try:
        WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, locator)))
    except TimeoutException:
        raise TimeOutException(by=by, locator=locator, timeout=timeout) from None
    except Exception as e:
        raise DriverException(e.__class__.__name__, str(e)) from None


def wait_until_not_visible(*, driver, locator, by=By.CSS_SELECTOR, timeout=10):
    by = check_xpath_by(by=by, locator=locator)
    try:
        for _ in range(timeout):
            if not driver.find_element(by=by, value=locator).is_displayed():
                return True
            time.sleep(1)
    except (NoSuchElementException, StaleElementReferenceException, TimeoutException, AttributeError):
        return True
    raise Exception(f"Target element ({by} locator [ {locator} ]) still visible after wait period.")


def element_exists(*, driver, locator, by=By.CSS_SELECTOR):
    by = check_xpath_by(by=by, locator=locator)
    for e in driver.find_elements(by=by, value=locator):
        if e.is_displayed():
            return True
    return False


class Element(object):
    def __init__(self, *, by, locator, web_element: RemoteWebElement):
        self.by = by
        self.locator = locator
        self._element = web_element

    def __repr__(self):
        return f"<Element object for {self.by} locator [ {self.locator} ]>"

    @property
    def driver(self):
        return self._element.parent

    @property
    def tag_name(self):
        return self._element.tag_name

    @property
    def text(self):
        return self._element.text

    # Wrapper methods around the actual WebElement's methods, allowing us to access them without using _element and also
    # to modify them when we need to.
    def click(self, *, wait=True, timeout=10, offset=0):
        try:
            if not wait:
                return self._element.click()

            clickable = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((self.by, self.locator)))
            if offset:
                ActionChains(self.driver).move_to_element_with_offset(clickable, 0, offset).click().perform()
            else:
                clickable.click()
        except Exception as e:
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

    @property
    def parent(self):
        return self._element.parent

    def find_element(self, value=None, *, by=By.CSS_SELECTOR):
        by = check_xpath_by(by=by, locator=value)
        new_element = self._element.find_element(by=by, value=value)
        return Element(by=by, locator=value, web_element=new_element)

    def find_elements(self, value=None, *, by=By.CSS_SELECTOR):
        by = check_xpath_by(by=by, locator=value)
        new_elements = self._element.find_elements(by=by, value=value)
        return [Element(by=by, locator=value, web_element=e) for e in new_elements]

    # Other methods
    def set_value(self, text):
        self.click()
        self.clear()
        self.send_keys(text)


class SelectElement(Element):
    def __init__(self, normal_element: Element):
        super().__init__(by=normal_element.by, locator=normal_element.locator, web_element=normal_element._element)
        self._select = Select(self._element)

    def select_text(self, text):
        return self._select.select_by_visible_text(text)

    def select_by_index(self, index):
        return self._select.select_by_index(index)

    def select_value(self, val):
        return self._select.select_by_value(val)
