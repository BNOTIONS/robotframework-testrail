#!/usr/bin/env python3
# -*- coding: UTF-8 -*-import ssl

""" This module publishes Robot Framework results to Testrail.

Once robot test suites are executed, this module is run to create a new test plan containing results of those test suites. 
Additionally, templates for Testrail test suites consisting of test cases are either:

    1. created new and pushed to Testrail, if the robot test suite result is being uplaoded for the first time, or test cases have 
       been added to the robot test suite. 
    2. updated, if the same robot test suites have been previously run and Testrail test suite templates already exist for them.

Example: 

New Robot Test Suites Executed -> Results Published to XML File 
This Script is Run-> Creates New Templates for Test Suites and their Test Cases on Testrail -> Creates New Test Plan 
displaying Results of Test Suites and their Test Cases

Re-Execution of Same Robot Test Suites -> New Results Overwritten to XML File 
This Script is Run -> Updates Existing Templates for Test Suites and their Test Cases on Testrail -> Creates New Test Plan 
displaying the Results of Test Suites and their Test Cases 

This module mainly uses the Testrail API and Robot API for data communication.
 
    The Robot API is utilized by implementing the class ResultVisitor with class TestRailResultVisiter. ResultVisitor finds the last 
    instanceof your robot test execution through the output XML file the Robot Framework generates after each test execution. 
    This allows the module to retrieve all the data from the last execution of your robot test suites through ResultVisitor. 
    
    The Testraul API is utilized to communicate with Testrail Cloud, allowing data access, retrieval and submission between this node
    and your Testrail cloud account. 

    Other supporting libraries are used to accomplish tasks such as: parse cli arguments, parse xml code, log data, format 
    console output, and format date and time 
"""
import os
import datetime
import configparser
import logging 
import argparse
import testrail
import sys
import re

from colorama import Fore, Style, init
from robot.api import ExecutionResult, ResultVisitor
from testrail_utils import TestRailApiUtils

PATH = os.getcwd()

COMMENT_SIZE_LIMIT = 1000

# Configure the logging
LOG_FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(filename=os.path.join(PATH, 'robotResult2Testrail.log'), format=LOG_FORMAT, level=logging.DEBUG)
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setLevel(logging.DEBUG)
CONSOLE_HANDLER.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(CONSOLE_HANDLER)



class TestRailResultVisitor(ResultVisitor):
    """ Implement a `Visitor` that retrieves TestRail Tags, Test Suite and Test Case Data from Robot Framework Result """
    
    
    def __init__(self):
        """ Init, list of suites and test cases, to be stored when suite data is retrieved  """
        self.suite_list = []
        self.testcase_list=[]

    def end_suite(self, suite):
        """ Called when suite end """
        for s, t in self._get_testsuites(suite):
            self._append_testrail_suite(s, t)

    @staticmethod
    def _get_testsuites(suite):
        """ Retrieve list of test suites and their test cases 
        """
        result = []
    
        # if test suite has a metadata tag UPLOAD_TO_TESTRAIL, parse all test suites and cases 
        for metadata in suite.metadata:
            if metadata == 'UPLOAD_TO_TESTRAIL':
                testcases = suite.tests
                result.append((suite, testcases))
                logging.debug("Metadata UPLOAD_TO_TESTRAIL identified. Robot Test Suite Data Ready To Be Uploaded From %s.py ", str(suite.name))
       
        return result

    def _append_testrail_suite(self, suite, testcases):
        """ Append and format test suite and case data in Testrail specific 
            JSON formatting 
        """
        suitename = suite.name
        self.suite_list.append({
            'name' : suitename
        })  
        
        for test in testcases:
            
            test_name = test.name
            test_current_status = test.status
            comment = None
            if test.message:
                comment = test.message
                # Indent text to avoid string formatting by TestRail. Limit size of comment.
                comment = "# Robot Framework result: #\n    " + comment[:COMMENT_SIZE_LIMIT].replace('\n', '\n    ')
                comment += '\n...\nLog truncated' if len(str(comment)) > COMMENT_SIZE_LIMIT else ''
            duration = 0
            if test.starttime and test.endtime:
                td_duration = datetime.datetime.strptime(test.endtime + '000', '%Y%m%d %H:%M:%S.%f')\
                            - datetime.datetime.strptime(test.starttime + '000', '%Y%m%d %H:%M:%S.%f')
                duration = round(td_duration.total_seconds())
                duration = 1 if (duration < 1) else duration    # TestRail API doesn't manage msec (min value=1s)
            
            
            self.testcase_list.append({
                'title': test_name, 
                'suite_name': suitename,
                'status': test_current_status, 
                'comment': comment,
                'duration': duration
            })

def get_result_data(xml_robot_output):
    """ Creates a result visitor from Robot API and accesses data from last Robot test run  """
    result = ExecutionResult(xml_robot_output)
    visitor = TestRailResultVisitor()
    result.visit(visitor)
    return visitor.suite_list, visitor.testcase_list

def get_rid(tc):
    """Get robot ID of test case assigned on robot test suite
       Parses robot xml output file   """  
    code = str(re.findall("(TC_?\d+)",tc))
    return code 

def get_robot_tc_ids(testcases):
    """Maps Robot test case ID to Testrail test case ID"""  
    tc_ids = dict()
    for test in testcases: 
        rid = str(re.findall("(TC_?\d+)", test['title']))
        tid = test['id']
        tc_ids.update({rid:tid})
    
    return tc_ids

def update_test_cases(api, tr_testcases, r_testcases, suite): 
    """ Updates existing/adds test cases on Testrail 
        :param api: Client to TestRail API
        :param r_testcases: List of test cases from Robot test suite
        :param tr_testcases: List of test cases + all data pertaining to test cases returned by Testrail
        :param suite: suite in which r_testcases exist under
    """
    
    if r_testcases: 
        for rtest in r_testcases: 
            if rtest['suite_name'] == suite['name']: 
                data = {'title':rtest['title']}
                if tr_testcases: 
                    robot_id = get_rid(rtest['title'])
                    robot_ids_on_tr = get_robot_tc_ids(tr_testcases)
                    
                    if robot_id in robot_ids_on_tr:
                        rtest['id'] = api.update_case(robot_ids_on_tr[robot_id], data)['id']
                        #logging.info("    Updating Test Case #%d", robot_ids_on_tr[robot_id])
                    else: 
                        rtest['id'] = api.add_case(suite['section_id'],data)['id']
                        logging.info("    Adding New Test Case #%s", rtest['title'])
                        
                else: 
                    rtest['id'] = api.add_case(suite['section_id'],data)['id']
                    logging.info("    Adding New Test Case #%s", rtest['title'])
    else: 
        logging.info('    There Are No Robot Test Cases Available To Add/Update To Testrail Suite #%s', suite['name'])
        
                


def update_robot_suites(api, testsuites, testcases, pid):
    """ Updates existing/add test suites and their test cases on Testrail 
        :param api: Client to TestRail API
        :param testsuites: List of test suites from Robot Framework 
        :param testcases: List of test cases belonging to each test suite from Robot Framework
        :param pid: Testrail project ID test suites are being updated/published to
        :return: True if updating was done. False in case of error.
    """ 
    
    tr_testsuites_list = api.get_suites(pid)
    logging.info('Retrieving List of Test Suites from Project #%d', pid)
        
    #add/update test suites
    if testsuites:
        
        isExisting = 0 
        
        for suite in testsuites:
            for d in tr_testsuites_list:
                if suite.items() <= d.items():
                    isExisting = 1 
                    break
            
            if isExisting: 
                #update test suite 
                suite['id'] = api.update_suite(d['id'], suite)['id']
                suiteid = suite['id']
                #leave section name blank 
                data = {'name':'', 'suite_id': suiteid}
                sectionid = api.get_sections(pid, suiteid)[0]['id']
                #api.delete_section(sectionid)
                suite['section_id']= sectionid 
                logging.info("Updating Testrail Test Suite #%d %s", suiteid, suite['name'])
                
            else:
                #add new test suite 
                suite['id'] = api.add_suite(pid, suite)['id']
                suiteid = suite['id']
                data = {'name':'section', 'suite_id': suiteid}
                suite['section_id'] = api.add_section(pid, data)['id']
                logging.info("Adding New Testrail Test Suite #%d %s", suiteid, suite['name'])
            
            #add/update test cases to suite
            update_test_cases(api, api.get_cases(pid, suiteid), testcases, suite)

        
    else: 
        logging.info('There Are No Robot Test Suites Available to Publish To Testrail Project #%d', pid)
        return False   
    
    return True  
  
    
def create_testrail_testplan(api, testsuites, testcases, pid):
    """ Creates new test plan on Testrail and uploads Robot results to it 
        :param api: Client to TestRail API
        :param testsuites: List of test suites from Robot Framework 
        :param testcases: List of test cases belonging to each test suite from Robot Framework
        :param pid: Testrail project ID test suites are being updated/published to
        :return: True if publishing was done. False in case of error.
    """ 
    
    try: 
        if update_robot_suites(api, testsuites, testcases, pid): 
            name = "Test Plan " + str(datetime.datetime.now())
            data_init = {'name': name}
            plan_id = api.add_plan(pid, data_init)['id']
            logging.info("Creating A New Testrail Test Plan %s For Project #%d...", name, pid)
            
            for suite in testsuites: 
                count = 0 
                data = {'suite_id':suite['id']}
                run_id = api.add_plan_entry(plan_id, data)['runs'][0]['id']
                logging.info("    Adding Suite #%d %s to New Test Run #%d", suite['id'], suite['name'], run_id)
                for test in testcases: 
                    if test['suite_name'] == suite['name']:
                        api.add_result_alt(run_id, test)
                        count += 1 
                        logging.info("        Adding Test Case #%d %s", test['id'], test['title'])
                logging.info('Added %d Test Case Results For Robot Test Suite %s into Test Plan %s', count, suite['name'], name)
            
            logging.info('Finished Publishing Results to Test Plan %s!', name)
        else: 
            logging.debug('Could Not Create Testrail Test Plan For Project  #%d', pid)
            return False 
    except testrail.APIError as error: 
        logging.error('Could Not Create Testrail Test Plan For Project #%d - Testrail API Error - %s', pid, str(error))
        
    return True 

              
def options():
    
    """ Manage options """
    parser = argparse.ArgumentParser(prog='robotResult2Testrail.py', description=__doc__)
    parser.add_argument(
        'xml_robot_output',
        nargs=1,
        type=argparse.FileType('r', encoding='UTF-8'),
        help='XML output results of Robot Framework')
    parser.add_argument(
        '--tr-config',
        dest='config',
        metavar='CONFIG',
        type=argparse.FileType('r', encoding='UTF-8'),
        required=True,
        help='TestRail configuration file.')
    parser.add_argument(
        '--tr-password', 
        dest='password', 
        metavar='API_KEY', 
        help='API key of TestRail account with write access.')
    parser.add_argument(
        '--tr-pid',
        dest='pid',
        action='store',
        type=int,
        default=None,
        help='Identifier of Project, that appears in TestRail.')

    opt = parser.parse_known_args()
    if opt[1]:
        logging.warning('Unknown options: %s', opt[1])
    return opt[0]
   
def uploadResults():
    
    ARGUMENTS = options()
    CONFIG = configparser.ConfigParser()
    CONFIG.read_file(ARGUMENTS.config)
    URL = CONFIG.get('API', 'url')
    EMAIL = CONFIG.get('API', 'email')
    PASSWORD = ARGUMENTS.password
    
    logging.debug('Connection info: URL=%s, EMAIL=%s, PASSWORD=%s', URL, EMAIL, len(PASSWORD) * '*')
    
    # Connect to Testrail/Init API 
    API = TestRailApiUtils(URL)
    API.user = EMAIL
    API.password = PASSWORD
    
    data = get_result_data(ARGUMENTS.xml_robot_output[0].name)
    
    TESTSUITES = data[0]
    TESTCASES = data[1]

    if create_testrail_testplan(API, TESTSUITES, TESTCASES, pid=ARGUMENTS.pid): 
        sys.exit()
    else: 
        sys.exit(1)
        print("Error")

# Main 
if __name__ == "__main__":
    uploadResults()
