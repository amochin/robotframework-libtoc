*** Keywords ***
Start Firefox with no proxy
	[Arguments]	${URL}
    ${proxy}=    Evaluate    sys.modules['selenium.webdriver'].Proxy()        sys, selenium.webdriver
    ${direct}=    Evaluate    sys.modules['selenium.webdriver'].common.proxy.ProxyType.DIRECT        sys, selenium.webdriver
    ${proxy.proxyType}=    Set Variable    ${direct}
    ${caps}=    Evaluate    sys.modules['selenium.webdriver'].DesiredCapabilities.FIREFOX        sys, selenium.webdriver
    Evaluate    $proxy.add_to_capabilities($caps)
    Open Browser	${URL}    Firefox

Open SUT X in Browser
    [Documentation]    Starts the browser und opens the SUT X start page
    No Operation