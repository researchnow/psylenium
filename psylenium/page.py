from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from selenium.common.exceptions import StaleElementReferenceException

from psylenium.exceptions import DriverException
from psylenium.element import Element


class Page(object):
    """
    :type driver: WebDriver
    :type elements: dict[str, Element]
    """
    def __init__(self, driver, url=None):
        self.driver = driver
        self.elements = {}
        self.url = url

    def go_to_page(self):
        if not self.url:
            raise ValueError("No URL defined for this Page class.")
        self.driver.get(self.url)

    def wait_for_element(self, by, locator, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, locator)))
        except Exception as e:
            raise DriverException(e.__class__.__name__, str(e)) from None

    def element_exists(self, locator, by=By.CSS_SELECTOR):
        for e in self.driver.find_elements(by=by, value=locator):
            if e.is_displayed():
                return True
        return False

    def find_element(self, locator, by=By.CSS_SELECTOR, wait=True, timeout=10):
        if wait:
            self.wait_for_element(by=by, locator=locator, timeout=timeout)
        element = self.driver.find_element(by=by, value=locator)
        return Element(by=by, locator=locator, web_element=element)

    def find_elements(self, locator, by=By.CSS_SELECTOR):
        elements = self.driver.find_elements(by=by, value=locator)
        return [Element(by=by, locator=locator, web_element=element) for element in elements]

    def element(self, locator, by=By.CSS_SELECTOR):
        """ Retrieval method for accessing Element objects on the page. It is the underlying method called by any
        property elements on Page classes; it checks its storage dict for the element in case it's already been
        accessed, and also checks if that element is still valid. If either of those checks fail, it looks up a new
        Element and stores it before returning. """
        
        if self.elements.get(locator):
            try:
                self.elements[locator].is_enabled()
            except StaleElementReferenceException:
                self.elements.pop(locator)
        if not self.elements.get(locator):
            self.elements[locator] = self.find_element(by=by, locator=locator)
        return self.elements[locator]


class PageComponent(object):
    """ An Element container class similar to the Page class, but smaller in scope - tethered to a single HTML element
     as its root instead of the DOM - and linked to a Page object that represents the DOM.
    """
    def __init__(self, *, page: Page, locator, by=By.CSS_SELECTOR):
        self.parent_page = page
        self.locator = locator
        self.by = by
        self.elements = {}

    def get(self):
        """ Retrieval method for the Element that represents the root of this part of the page. """
        return self.parent_page.element(by=self.by, locator=self.locator)

    def find_element(self, locator, by=By.CSS_SELECTOR):
        element = self.get().find_element(by=by, value=locator)
        return element

    def find_elements(self, locator, by=By.CSS_SELECTOR):
        elements = self.get().find_elements(by=by, value=locator)
        return elements

    def element(self, locator, by=By.CSS_SELECTOR) -> Element:
        if self.elements.get(locator):
            try:
                self.elements[locator].is_enabled()
            except StaleElementReferenceException:
                self.elements.pop(locator)
        if not self.elements.get(locator):
            self.elements[locator] = self.get().find_element(by=by, value=locator)
        return self.elements[locator]

    def click(self):
        return self.get().click()

    def clear(self):
        return self.get().clear()

    def get_attribute(self, name):
        return self.get().get_attribute(name)

    def is_selected(self):
        return self.get().is_selected()

    def is_enabled(self):
        return self.get().is_enabled()

    def is_displayed(self):
        return self.get().is_displayed()

    def send_keys(self, *value):
        return self.get().send_keys(*value)


class SubComponent(PageComponent):
    """ An extension of the PageComponent class that is built for nesting components. Tied to a PageComponent parent
    instead of the overall Page. """
    def __init__(self, parent: PageComponent, locator, by=By.CSS_SELECTOR):
        self.parent = parent
        super().__init__(page=parent.parent_page, locator=locator, by=by)

    def get(self):
        return self.parent.element(by=self.by, locator=self.locator)
