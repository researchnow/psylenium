from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from selenium.common.exceptions import StaleElementReferenceException

from psylenium.exceptions import DriverException
from psylenium.element import Element, check_xpath_by, wait_for_element, wait_until_not_visible, element_exists


class Page(object):
    """
    :type driver: WebDriver
    :type elements: dict[str, Element]
    """

    def __init__(self, driver, url=None, default_timeout=5, waits_enabled=True):
        self.driver = driver
        self.elements = {}
        self.url = url

        self.timeout = default_timeout
        self.no_waits = not waits_enabled

    def __repr__(self):
        return f"<{self.__class__.__name__} Page object with browser at {self.driver.current_url}>"

    def go_to_page(self):
        if not self.url:
            raise ValueError("No URL defined for this Page class.")
        self.driver.get(self.url)

    def wait_for_element(self, locator, *, by=By.CSS_SELECTOR, timeout=None, visible=True):
        timeout = self.timeout if timeout is None else timeout
        wait_for_element(driver=self.driver, by=by, locator=locator, timeout=timeout, visible=visible)

    def wait_until_not_visible(self, locator, *, by=By.CSS_SELECTOR, timeout=2):
        return wait_until_not_visible(driver=self.driver, by=by, locator=locator, timeout=timeout)

    def element_exists(self, locator, by=By.CSS_SELECTOR):
        return element_exists(driver=self.driver, by=by, locator=locator)

    def find_element(self, locator, by=By.CSS_SELECTOR, wait=True, timeout=None, visible=True):
        by = check_xpath_by(by=by, locator=locator)
        timeout = self.timeout if timeout is None else timeout
        if wait and not self.no_waits:
            self.wait_for_element(by=by, locator=locator, timeout=timeout, visible=visible)
        try:
            element = self.driver.find_element(by=by, value=locator)
        except Exception as e:
            raise DriverException(e.__class__.__name__, str(e)) from None
        return Element(by=by, locator=locator, web_element=element)

    def find_elements(self, locator, by=By.CSS_SELECTOR):
        by = check_xpath_by(by=by, locator=locator)
        elements = self.driver.find_elements(by=by, value=locator)
        return [Element(by=by, locator=locator, web_element=element) for element in elements]

    def element(self, locator: str, *, by=By.CSS_SELECTOR, visible=True) -> Element:
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
            self.elements[locator] = self.find_element(by=by, locator=locator, visible=visible)
        return self.elements[locator]

    def get_xpath_results_from_js(self, xpath, attribute, result_type="ORDERED_NODE_ITERATOR_TYPE"):
        """ A standard JavaScript statement block that executes the provided XPath and returns the results as a list.
        This can be used to evaluate XPaths without having to deal with the elements themselves, like when you just need
        the IDs. """

        empty = """ var iter = document.evaluate("<xpath>", document, null, XPathResult.<rtype>, null);
                    var arrayXpath = new Array();
                    var thisNode = iter.iterateNext();
                    while (thisNode) {
                        arrayXpath.push(thisNode.<attr>);
                        thisNode = iter.iterateNext();
                    }
                    return arrayXpath; """
        script = empty.replace("<xpath>", xpath).replace("<attr>", attribute).replace("<rtype>", result_type)
        results = self.driver.execute_script(script)
        return results


class PageComponent(object):
    """ An Element container class similar to the Page class, but smaller in scope - tethered to a single HTML element
     as its root instead of the DOM - and linked to a Page object that represents the DOM. Essentially, this is a
     child class of both Page and Element, so it includes accessors for the methods from Element.

    :type parent_page: Page
    :type elements: dict[str, Element]
    """

    def __init__(self, *, page: Page, locator: str, by=By.CSS_SELECTOR, visible=True):
        self.parent_page = page
        self.locator = locator
        self.by = by
        self.visible = visible
        self.elements = {}

        self.timeout = page.timeout
        self.no_waits = False

    def __repr__(self):
        return f"<{self.__class__.__name__} PageComponent object rooted at {self.by} locator [ {self.locator} ]>"

    @property
    def driver(self):
        return self.parent_page.driver

    def get(self) -> Element:
        """ Retrieval method for the Element that represents the root of this part of the page. """
        return self.parent_page.element(by=self.by, locator=self.locator, visible=self.visible)

    def wait_for_self(self, *, timeout: int=None):
        """ Built-in wait method that waits for the PageComponent's root element to appear on the page. """
        timeout = self.timeout if timeout is None else timeout
        return self.parent_page.wait_for_element(locator=self.locator, by=self.by, timeout=timeout)

    def wait_for_element(self, locator, *, by=By.CSS_SELECTOR, timeout: int=None, visible=True):
        timeout = self.timeout if timeout is None else timeout
        wait_for_element(driver=self.driver, by=by, locator=locator, timeout=timeout, visible=visible)

    def wait_until_not_visible(self, locator, *, by=By.CSS_SELECTOR, timeout=2):
        return wait_until_not_visible(driver=self.driver, by=by, locator=locator, timeout=timeout)

    def element_exists(self, locator, by=By.CSS_SELECTOR):
        return element_exists(driver=self.driver, by=by, locator=locator)

    def find_element(self, locator, by=By.CSS_SELECTOR, wait=True, timeout: int=None, visible=True):
        timeout = self.timeout if timeout is None else timeout
        if wait and not self.no_waits:
            self.wait_for_element(by=by, locator=locator, timeout=timeout, visible=visible)
        return self.get().find_element(by=by, value=locator)

    def find_elements(self, locator, by=By.CSS_SELECTOR):
        return self.get().find_elements(by=by, value=locator)

    def element(self, locator, *, by=By.CSS_SELECTOR, visible=True) -> Element:
        """ This function works the same as the Page class's element() method, except that it will invoke find_element()
        against the PageComponent's root Element object. This will only search from that DOM element downward instead
        of throughout the entire DOM. """

        if self.elements.get(locator):
            try:
                self.elements[locator].is_enabled()
            except StaleElementReferenceException:
                self.elements.pop(locator)
        if not self.elements.get(locator):
            self.elements[locator] = self.find_element(by=by, locator=locator, visible=visible)
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

    def set_value(self, text, *, tab=False):
        return self.get().set_value(text=text, tab=tab)


class SubComponent(PageComponent):
    """ An extension of the PageComponent class that is built for nesting components. Tied to a PageComponent parent
    instead of the overall Page.

    :type parent: PageComponent
    """

    def __init__(self, *, parent: PageComponent, locator: str, by=By.CSS_SELECTOR, visible=True):
        self.parent = parent
        super().__init__(page=parent.parent_page, locator=locator, by=by, visible=visible)

    def __repr__(self):
        return f"<{self.__class__.__name__} SubComponent object rooted at {self.by} locator [ {self.locator} ]>"

    def get(self):
        return self.parent.element(by=self.by, locator=self.locator)
