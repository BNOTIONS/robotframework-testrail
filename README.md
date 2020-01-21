robotframework-testrail
=======================

This script creates/updates Test Suite and Test Case templates from Robot Framework tests, and publishes results to a new Test Plan in TestRail. 

The standard process is:
Robot Framework execution => `output.xml` => This script => TestRail API


Installation
------------

Tested with Python>=3.

Best use with `virtualenv` (to adapt according your Python/OS version):
    
```cmd
> virtualenv .
> Scripts\activate  # Windows case
> pip install -r requirements.txt
```


Configuration
-------------

### Robot Framework

You must add a metadata tag to your test suite file called `UPLOAD_TO_TESTRAIL` and label your Test Cases starting with TC_<TEST_CASE_NUMBER). The TEST_CASE_NUMBER should be in ascending order from 1-n, n=number of Test Cases in each Test Suite.  

Format of Test Case Title :

* `TC_` + unique integer + space + title of your Test Case: `TC_2 Verify Toggle Button`, `TC_2 Validate Login`
* unique integer: 1 - n, n=number of Test Cases in each Test Suite. Each Test Case should be labeled with an integer in ascending order. 


**Example**:
```robotframework
*** Settings ***
Metadata          UPLOAD_TO_TESTRAIL 

*** Test Cases ***

TC_1 Verify buying mode toggle label   
    Launch The Application in buying mode
TC_2 Verify the buying and selling mode 
    Go To    ${HOMEPAGE}
TC_3 Verify all the tabs labels 
    Launch the application in buying mode
    click on get ready tab in buying mode
    click on Browse property tab in buying mode
```

In this case, the result of Test Case C345 will be 'passed' in TestRail.


**With Tags:**

If you want to create one or more than `TEST_CASE_ID` for your test or tests use the following method:

Create a tag `test_case_id=ID` in your test containing TestRail ID without a metadata `TEST_CASE_ID`.

Format of ID is:
* `C` + an integer: `C1234`
* An integer: 1234, 5678

**Example one test**:
```robotframework
*** Test Cases ***
Test 1
    [Tags]  test_case_id=1234   critical standard
```

**Example more than one test**:
```robotframework
*** Test Cases ***
Test 1
    [Tags]  test_case_id=C1234   critical standard
    
Test 2
    [Tags]  test_case_id=C5678   critical standard
    
Test 3
    [Tags]  test_case_id=C91011   critical standard
```
In this case, the results of Test 1 C1234 and Test 2 C5678 and Test 3 C91011 will be 'passed' in TestRail.

**Example priority management**:
```robotframework
*** Settings ***
Metadata          TEST_CASE_ID    C345

*** Test Cases ***

Test Example
Test 1
    [Tags]  test_case_id=C1234   critical standard
```
In this case, the result of Test Case C1234 will be 'passed' in TestRail and not C345, priority to tag and not metatdata.

**Other examples**
You can find more examples in `test/examples` folder.

### TestRail configuration

Create a configuration file (`testrail.cfg` for instance) containing following parameters:

```ini
[API]
url = https://yoururl.testrail.net/
email = user@email.com
password = <api_key> # May be set in command line
```

**Note** : `password` is an API key that should be generated with your TestRail account in "My Settings" section.

Usage
-----

```
usage: robotframework2testrail.py [-h] --tr-config CONFIG
                                  [--tr-password API_KEY]
                                  [--tr-pid PROJECT_ID | --tr-plan-id PLAN_ID]
                                  xml_robotfwk_output

Tool to publish Robot Framework results in TestRail

positional arguments:
  xml_robotfwk_output   XML output results of Robot Framework

optional arguments:
  -h, --help            show this help message and exit
  --tr-config CONFIG    TestRail configuration file.
  --tr-password API_KEY
                        API key of TestRail account with write access.
  --tr-pid PROJECT_ID  Identifier of TestRail Project, that appears in TestRail.
```

### Example

```bash

# Publish a Test Plan for Project #1 a
python robotResult2Testrail.py --tr-config=testrail.cfg --tr-password samplepassword123 --tr-pid=1 output.xml


