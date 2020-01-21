import ssl
import os
import datetime
import configparser
import argparse
import testrail
import re

from colorama import Fore, Style, init
from robot.api import ExecutionResult, ResultVisitor
from testrail_utils import TestRailApiUtils

COMMENT_SIZE_LIMIT = 1000

class TestRailResultVisitor(ResultVisitor):
    """ Implement a `Visitor` that retrieves TestRail ID from Robot Framework Result """
        
    def __init__(self):
        """ Init """
        self.suite_list = []
        self.testcase_list=[]

    def end_suite(self, suite):
        """ Called when suite end """
        for s, t in self._get_testsuites(suite):
            self._append_testrail_suite(s, t)

    @staticmethod
    def _get_testsuites(suite):
        """ Retrieve list of testsuites and its test cases 
        """
        result = []
        
        # Retrieve test_cases from suites 
        for metadata in suite.metadata:
            if metadata == 'UPLOAD_TO_TESTRAIL':
                testcases = suite.tests
                result.append((suite, testcases))
          
       
        return result

    def _append_testrail_suite(self, suite, testcases):
        
        suitename = suite.name
        self.suite_list.append({
            'name' : suitename
        })  
        
        for test in testcases:
            
            test_name = test.name
            test_current_status = test.status
            """ Append a result in TestRail format """
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
    """ Return the list of Testcase ID with status """
    result = ExecutionResult(xml_robot_output)
    visitor = TestRailResultVisitor()
    result.visit(visitor)
    return visitor.suite_list, visitor.testcase_list


def update_test_cases(api, tr_testcases, r_testcases, suite): 
    
    for rtest in r_testcases: 
        if rtest['suite_name'] == suite['name']: 
            data = {'title':rtest['title']}
            if tr_testcases: 
                robot_id = get_rid(rtest['title'])
                robot_ids_on_tr = get_robot_tc_ids(tr_testcases)
                
                if robot_id in robot_ids_on_tr:
                    rtest['id'] = api.update_case(robot_ids_on_tr[robot_id], data)['id']
                    print("Updating Test Case ", robot_ids_on_tr[robot_id])
                else: 
                    rtest['id'] = api.add_case(suite['section_id'],data)['id']
                    print("Adding New Test Case ", rtest['title'])
                    
            else: 
                rtest['id'] = api.add_case(suite['section_id'],data)['id']
                print("Adding New Testcase ", rtest['title'])
                
#get robot id of testcase assigned on robot test suite 
def get_rid(tc):  
    code = str(re.findall("(TC_?\d+)",tc))
    return code 

def get_robot_tc_ids(testcases):
    
    tc_ids = dict()
    for test in testcases: 
        rid = str(re.findall("(TC_?\d+)", test['title']))
        tid = test['id']
        tc_ids.update({rid:tid})
    
    return tc_ids

def publish_suites(api, testsuites, testcases, pid):
    
    tr_testsuites_list = api.get_suites(pid)
    
    isExisting = 0 
    
    #add testsuites
    for suite in testsuites:
        for d in tr_testsuites_list:
            if suite.items() <= d.items():
                isExisting = 1 
                break
        
        if isExisting: 
            suite['id'] = api.update_suite(d['id'], suite)['id']
            suiteid = suite['id']
            data = {'name':'section', 'suite_id': suiteid}
            sectionid = api.get_sections(pid, suiteid)[0]['id']
            #api.delete_section(sectionid)
            
            suite['section_id']= sectionid 
            
            
        else:
            suite['id'] = api.add_suite(pid, suite)['id']
            suiteid = suite['id']
            data = {'name':'section', 'suite_id': suiteid}
            suite['section_id'] = api.add_section(pid, data)['id']
            print("Suite ", suite, " has been added")
        
        #add testcases 
        update_test_cases(api, api.get_cases(pid, suiteid), testcases, suite)
    
  
    
def publish_testplan(api, testsuites, testcases, pid):   
   
    name = "Test Plan " + str(datetime.datetime.now())
    data_init = {'name': name}
    plan_id = api.add_plan(pid, data_init)['id']
    
    for suite in testsuites: 
        data = {'suite_id':suite['id']}
        run_id = api.add_plan_entry(plan_id, data)['runs'][0]['id']
        for test in testcases: 
            if test['suite_name'] == suite['name']:
                api.add_result_alt(run_id, test)
        
        print("Added Test Run: ", suite['name'], " to Test Plan: ", name)
                
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
   

def uploadTestSuite():
    
    ssl._create_default_https_context = ssl._create_unverified_context
    
    ARGUMENTS = options()
    CONFIG = configparser.ConfigParser()
    CONFIG.read_file(ARGUMENTS.config)
    URL = CONFIG.get('API', 'url')
    EMAIL = CONFIG.get('API', 'email')
    PASSWORD = CONFIG.get('API', 'password')
    #to connect to testrail 
    API = TestRailApiUtils(URL)
    API.user = EMAIL
    API.password = PASSWORD
    
    data = get_result_data(ARGUMENTS.xml_robot_output[0].name)
    
    TESTSUITES = data[0]
    TESTCASES = data[1]

    publish_suites(API, TESTSUITES, TESTCASES, pid=ARGUMENTS.pid)
    publish_testplan(API, TESTSUITES, TESTCASES, pid=ARGUMENTS.pid)

if __name__ == "__main__":
    uploadTestSuite()
