from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from selenium.common.exceptions import StaleElementReferenceException

from psylenium.element import Element, check_if_by_should_be_xpath, wait_for_element, wait_until_not_visible, \
    element_exists, is_element_visible
from psylenium.exceptions import DriverException


class DOMObject(object):
    """
    :type elements: dict[str, Element]
    """
    def __init__(self, *, waits_enabled=True, default_timeout: int):
        self.elements = {}

        self.waits_enabled = waits_enabled
        self.default_timeout = default_timeout

    @property
    def _selenium_root(self):
        """ Used to force Selenium methods/waits to work relative to the specified target, instead of giving it the
         driver and thus searching from the start of the DOM. The Page class will simply return the driver, but
         PageComponent will return the WebElement representing the HTML element they are rooted at. """
        raise NotImplementedError("All DOMObject classes must define their Selenium root, which is either the driver,"
                                  "or the WebElement from the class's root Element.")

    # # #
    # Accessor methods for the find/visible/exists methods, relative to the class's Selenium root (driver or element).
    # # #
    def wait_for_element(self, locator, *, by=By.CSS_SELECTOR, timeout=None, visible=True):
        timeout = self.default_timeout if timeout is None else timeout
        wait_for_element(driver=self._selenium_root, by=by, locator=locator, timeout=timeout, visible=visible)

    def wait_until_not_visible(self, locator, *, by=By.CSS_SELECTOR, timeout=5):
        wait_until_not_visible(driver=self._selenium_root, by=by, locator=locator, timeout=timeout)

    def is_element_visible(self, locator, *, by=By.CSS_SELECTOR):
        return is_element_visible(driver=self._selenium_root, by=by, locator=locator)

    def element_exists(self, locator, by=By.CSS_SELECTOR):
        return element_exists(driver=self._selenium_root, by=by, locator=locator)

    def find_element(self, locator, *, by=By.CSS_SELECTOR, wait=True, timeout=None, visible=True):
        """ :rtype: Element """
        raise NotImplementedError("find_element must be implemented by all direct child classes of DOMObject.")

    def find_elements(self, locator, by=By.CSS_SELECTOR):
        """ :rtype: list[Element] """
        raise NotImplementedError("find_elements must be implemented by all direct child classes of DOMObject.")

    def element(self, locator, *, by=By.CSS_SELECTOR, visible=False) -> Element:
        """ Retrieval method for accessing Element objects on the page. It is the underlying method called by any
        property elements on DOMObject classes; it checks its storage dict for the element in case it's already been
        accessed, and also checks if that element is still valid. If either of those checks fail, it looks up a new
        Element and stores it before returning.

        The actual implementation of how the DOMObject looks up new Elements will differ between child classes.

        This function works the same as the Page class's element() method, except that it will invoke find_element()
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


class Page(DOMObject):
    """
    :type driver: WebDriver
    """

    def __init__(self, driver, *, url=None, default_timeout=5, waits_enabled=True):
        super().__init__(waits_enabled=waits_enabled, default_timeout=default_timeout)
        self.driver = driver
        self.url = url

    def __repr__(self):
        return f"<{self.__class__.__name__} Page object with browser at {self.driver.current_url}>"

    @property
    def _selenium_root(self):
        return self.driver

    def go_to_page(self):
        if self.url is None:
            raise RuntimeError("No URL defined for this Page class.")
        self.driver.get(self.url)

    @property
    def current_url(self):
        return self.driver.current_url

    def find_element(self, locator, by=By.CSS_SELECTOR, *, wait=True, timeout=None, visible=True):
        """ Invokes `find_element` against the driver, which searches throughout the entire DOM. For all other DOMObject
         child classes, they should only ever invoke the `find_element` of their root Element class instead of the
         driver. """

        by = check_if_by_should_be_xpath(by=by, locator=locator)
        if wait and self.waits_enabled:
            self.wait_for_element(by=by, locator=locator, timeout=timeout, visible=visible)
        try:
            element = self.driver.find_element(by=by, value=locator)
        except Exception as e:
            raise DriverException(e.__class__.__name__, str(e)) from None
        return Element(by=by, locator=locator, web_element=element)

    def find_elements(self, locator, by=By.CSS_SELECTOR):
        by = check_if_by_should_be_xpath(by=by, locator=locator)
        elements = self.driver.find_elements(by=by, value=locator)
        return [Element(by=by, locator=locator, web_element=element) for element in elements]

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


class PageComponent(DOMObject):
    """ An Element container class similar to the Page class, but smaller in scope - tethered to a single HTML element
     as its root instead of the DOM - and linked to a Page object that represents the DOM. Essentially, this is a
     child class of both Page and Element, so it includes accessors for the methods from Element.

    :type parent: DOMObject
    """

    def __init__(self, parent: DOMObject, *, locator: str, by=By.CSS_SELECTOR, visible=True, default_timeout: int=None,
                 waits_enabled=True):
        default_timeout = parent.default_timeout if default_timeout is None else default_timeout
        super().__init__(waits_enabled=waits_enabled, default_timeout=default_timeout)
        self.parent = parent
        self.locator = locator
        self.by = by
        self.visible = visible

    def __repr__(self):
        string = f"{self.__class__.__name__} PageComponent object rooted at {self.by} locator [ {self.locator} ]"
        if isinstance(self.parent, PageComponent):
            return f"<{string}, within {self.parent.__class__.__name__} PageComponent>"
        return f"<{string}>"

    # noinspection PyProtectedMember
    @property
    def _selenium_root(self):
        """ Used to force Selenium methods/waits to work relative to the target element, instead of giving it the driver
         and thus searching from the start of the DOM. """
        return self.get()._element

    @property
    def parent_page(self):
        """ Accessor for the Page; for nested PageComponents, it's recursive. """
        if isinstance(self.parent, Page):
            return self.parent
        elif isinstance(self.parent, PageComponent):
            return self.parent.parent_page
        raise RuntimeError("Unexpected state; parent should only be a Page or PageComponent.")

    @property
    def driver(self):
        return self.parent_page.driver

    def get(self, visible: bool=None) -> Element:
        """ Retrieval method for the Element that represents the root of this part of the page. """
        visible = self.visible if visible is None else visible
        return self.parent.element(by=self.by, locator=self.locator, visible=visible)

    def wait_for_self(self, *, timeout: int=None):
        """ Built-in wait method that waits for the PageComponent's root element to appear on the page. """
        timeout = self.default_timeout if timeout is None else timeout
        self.parent.wait_for_element(locator=self.locator, by=self.by, timeout=timeout, visible=self.visible)

    def wait_until_absent(self, *, timeout: int = None):
        """ The reverse of wait_for_self; waits until the root element is no longer present/visible. """
        timeout = self.default_timeout if timeout is None else timeout
        self.wait_until_not_visible(locator="/.", timeout=timeout)

    def find_element(self, locator, *, by=By.CSS_SELECTOR, wait=True, timeout: int=None, visible=True):
        """ Invokes find_element against the root Element, which will only search from that DOM element downward
        instead of throughout the entire DOM."""
        if wait and self.waits_enabled:
            self.wait_for_element(by=by, locator=locator, timeout=timeout, visible=visible)
        return self.get().find_element(by=by, value=locator)

    def find_elements(self, locator, by=By.CSS_SELECTOR):
        return self.get().find_elements(by=by, value=locator)

    # # #
    # Accessor methods for common methods on the PageComponent's root Element.
    # # #
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
        return self.get(visible=False).is_displayed()

    def send_keys(self, *value):
        return self.get().send_keys(*value)

    def set_value(self, text, *, tab=False):
        return self.get().set_value(text=text, tab=tab)
