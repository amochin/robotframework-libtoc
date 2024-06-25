from robot.libraries.BuiltIn import BuiltIn

PAGE_TITLE = 'Some title'


def _s():
    return BuiltIn().get_library_instance('SeleniumLibrary')

locators = {
    "some_element": "//label[contains(text(), 'Blahblah')]/../..//input",
}

# ------ RF keywords -----------------------


def wait_page_loaded(timeout):
    """
    Waits for the page to load (meaning the element XYZ is visible), maximum the specified timeout.
    If the element is still not visible after timeout, an error is reported.
    
    _Parameters:_
        - *timeout* - Max. time to wait
    """
    _s().wait_until_page_contains_element(locators["some_element"], timeout=timeout)