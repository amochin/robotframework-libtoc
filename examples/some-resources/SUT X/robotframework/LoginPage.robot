*** Settings ***
Resource    Common.robot    

*** Variables ***

# Locators
${LoginDummy URL}    /login
${Login Button}    //button[text()='Login']

*** Keywords ***

Open
    [Documentation]        Navigates to the 'Login' page and waits for the 'Login' button to appear
    ...
    ...    _Parameters_:
    ...        - *Base_URL* - Base address of the SUT X app incl. prefix und port number
    [Arguments]    ${Base_URL}
    
    Go To    ${Base_URL}${LoginDummy URL}
    Wait Until Page Contains Element    ${Login Button}
    
Click Login
    [Documentation]    Clicks the 'Login' button
    Click Element    ${Login Button}