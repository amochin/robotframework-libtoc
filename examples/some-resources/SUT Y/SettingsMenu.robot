*** Settings ***
Resource    Common.robot    

*** Variables ***

# Locators
${Settings Page URL}    /settings
${Save Button}    //button[text()='Save']

*** Keywords ***

Navigate
    [Documentation]        Navigates to the Settings pages and waits for the "Save" button to appear
    ...
    ...    _Parameters_:
    ...        - *Base_URL* - Base URL of the SUT Y app including prefix und port number
    [Arguments]    ${Base_URL}
    
    Go To    ${Base_URL}${Settings Page URL}
    Wait Until Page Contains Element    ${Save Button}
    
Click Save
    [Documentation]    Clicks the 'Save' button
    Click Element    ${Save Button}     