#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" Various useful class using TestRail API """
import logging
import string

import testrail

API_ADD_RESULT_CASE_URL = 'add_result_for_case/{run_id}/{case_id}'
API_GET_RUN_URL = 'get_run/{run_id}'
API_GET_PLAN_URL = 'get_plan/{plan_id}'
API_GET_TESTS_URL = 'get_tests/{run_id}'
API_GET_SUITES_URL = 'get_suites/{project_id}'
API_GET_SUITE_URL = 'get_suite/{suite_id}'
API_ADD_SUITE_URL = 'add_suite/{project_id}'
API_UPDATE_SUITE_URL = 'update_suite/{suite_id}'
API_GET_CASES_URL = 'get_cases/{project_id}/{suite_id}'
API_ADD_CASE_URL = 'add_case/{section_id}'
API_UPDATE_CASE_URL = 'update_case/{case_id}'
API_ADD_SECTION_URL = 'add_section/{project_id}'
API_GET_SECTIONS_URL = 'get_sections/{project_id}&suite_id={suite_id}'
API_GET_CASES_URL = 'get_cases/{project_id}&suite_id={suite_id}'
API_DELETE_SECTION_URL = 'delete_section/{section_id}'
API_ADD_PLAN_URL = 'add_plan/{project_id}'
API_ADD_PLAN_ENTRY_URL = 'add_plan_entry/{plan_id}'


ROBOTFWK_TO_TESTRAIL_STATUS = {
    "PASS": 1,
    "FAIL": 5,
}


class TestRailApiUtils(testrail.APIClient):
    """ Class adding facilities to manipulate Testrail API """

    def add_result(self, testrun_id, testcase_info):
        """ Add a result to the given Test Run
        :param testrun_id: Testrail ID of the Test Run to feed
        :param testcase_info: Dict containing info on testcase
        """
        data = {'status_id': ROBOTFWK_TO_TESTRAIL_STATUS[testcase_info.get('status')]}
        if 'version' in testcase_info:
            data['version'] = testcase_info.get('version')
        if 'comment' in testcase_info:
            data['comment'] = testcase_info.get('comment')
        if 'duration' in testcase_info:
            data['elapsed'] = str(testcase_info.get('duration')) + 's'
        testcase_id = self.extract_testcase_id(testcase_info['id'])
        if not testcase_id:
            logging.error('Testcase ID is bad formatted: "%s"', testcase_info['id'])
            return None

        return self.send_post(API_ADD_RESULT_CASE_URL.format(run_id=testrun_id, case_id=testcase_id), data)
    
    def add_result_alt(self, testrun_id, testcase_info):
        """ Add a result to the given Test Run
        :param testrun_id: Testrail ID of the Test Run to feed
        :param testcase_info: Dict containing info on testcase
        """
        data = {'status_id': ROBOTFWK_TO_TESTRAIL_STATUS[testcase_info.get('status')]}
        if 'version' in testcase_info:
            data['version'] = testcase_info.get('version')
        if 'comment' in testcase_info:
            data['comment'] = testcase_info.get('comment')
        if 'duration' in testcase_info:
            data['elapsed'] = str(testcase_info.get('duration')) + 's'
        testcase_id = testcase_info.get('id')

        return self.send_post(API_ADD_RESULT_CASE_URL.format(run_id=testrun_id, case_id=testcase_id), data)

    def is_testrun_available(self, testrun_id):
        """ Ask if Test Run is available in TestRail.
        :param testplan_id: Testrail ID of the Test Run
        :return: True if Test Run exists AND is open
        """
        try:
            response = self.send_get(API_GET_RUN_URL.format(run_id=testrun_id))
            return response['is_completed'] is False
        except testrail.APIError as error:
            logging.error(error)
            return False
    
    #add 
    def is_testsuite_available(self, testsuite_id):
        """ Ask if Test Suite is available in TestRail.
        :param testsuite_id: Testrail ID of the Testsuite
        :return: True if Testsuite exists AND is open
        """
        try:
            response = self.send_get(API_GET_SUITE_URL.format(suite_id=testsuite_id))
            return response['is_completed'] is False
        except testrail.APIError as error:
            logging.error(error)
            return False

    def is_testplan_available(self, testplan_id):
        """ Ask if Test Plan is available in TestRail.
        :param testplan_id: Testrail ID of the Test Plan
        :return: True if Test Plan exists AND is open
        """
        try:
            response = self.send_get(API_GET_PLAN_URL.format(plan_id=testplan_id))
            return response['is_completed'] is False
        except testrail.APIError as error:
            logging.error(error)
            return False

    def get_available_testruns(self, testplan_id):
        """ Get the list of available Test Runs contained in a Test Plan
        :param testplan_id: Testrail ID of the Test Plan
        :return: List of available Test Runs associated to a Test Plan in TestRail.
        """
        testruns_list = []
        response = self.send_get(API_GET_PLAN_URL.format(plan_id=testplan_id))
        for entry in response['entries']:
            for run in entry['runs']:
                if not run['is_completed']:
                    testruns_list.append(run['id'])
        return testruns_list

    @staticmethod
    def extract_testcase_id(str_content):
        """ Extract testcase ID (TestRail) from the given string.
            :param str_content: String containing a testcase ID.
            :return: Testcase ID (int). `None` if not found.
        """
        testcase_id = None

        # Manage multiple value but take only the first chunk
        list_content = str_content.split()
        if list_content:
            first_chunk = list_content[0]
            try:
                testcase_id_str = ''.join(char for char in first_chunk if char in string.digits)
                testcase_id = int(testcase_id_str)
            except (TypeError, ValueError) as error:
                logging.error(error)

        return testcase_id

    def get_tests(self, testrun_id):
        try:
            return self.send_get(API_GET_TESTS_URL.format(run_id=testrun_id))
        except testrail.APIError as error:
            logging.error(error)
            
    def get_suites(self,pid):
        try:
            return self.send_get(API_GET_SUITES_URL.format(project_id=pid))
        except testrail.APIError as error:
            logging.error(error)
            
    def add_suite(self, pid, data):
        return self.send_post(API_ADD_SUITE_URL.format(project_id=pid), data)
    
    def update_suite(self, sid, data):
        return self.send_post(API_UPDATE_SUITE_URL.format(suite_id=sid), data)
    
    
    def get_cases(self, pid, suiteid):
        try:
            return self.send_get(API_GET_CASES_URL.format(project_id=pid, suite_id=suiteid))
        except testrail.APIError as error:
            logging.error(error)
    
    def add_case(self, sid, data):
        return self.send_post(API_ADD_CASE_URL.format(section_id=sid), data)
    
    def update_case(self, cid, data):
        return self.send_post(API_UPDATE_CASE_URL.format(case_id=cid), data)
    
    
    def add_section(self, pid, data):
        return self.send_post(API_ADD_SECTION_URL.format(project_id=pid), data)
    
    def get_sections(self, pid, sid):
        try:
            return self.send_get(API_GET_SECTIONS_URL.format(project_id=pid, suite_id = sid))
        except testrail.APIError as error:
            logging.error(error)
    
    #not sure if we need this       
    def delete_section(self, secid):
        return self.send_post(API_DELETE_SECTION_URL.format(section_id=secid), None)
    
    def get_cases(self, pid, sid):
        try:
            return self.send_get(API_GET_CASES_URL.format(project_id=pid, suite_id = sid))
        except testrail.APIError as error:
            logging.error(error)
            
    def add_plan(self, pid, data):
        return self.send_post(API_ADD_PLAN_URL.format(project_id=pid), data)
    
    
    def add_plan_entry(self, plid, data):
        return self.send_post(API_ADD_PLAN_ENTRY_URL.format(plan_id=plid), data)