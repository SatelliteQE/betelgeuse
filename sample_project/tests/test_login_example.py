# coding=utf-8
"""Test class for Login

:requirement: Importer Test
"""

import unittest


class LoginTestCase(unittest.TestCase):
    """Tests for Login"""

    def test_login_1(self):
        """Check if a user is able to login with valid userid and password

        :id: 60e48736-43a9-11e6-bcaa-104a7da122d7

        :steps: Login to UI with valid userid and password

        :expectedresults: User is able to login successfully
        """
        pass

    def test_login_2(self):
        """This is an expected failure

        :id: 5adbfbe3-9594-46bb-b8b6-d8ef3dbca6b6

        :steps:

            1. First Step
            2. Second Step

        :expectedresults:

            1. First Result
            2. Second Result
        """
        self.fail('Expected failure')

    def test_login_3(self):
        """This is an expected skip

        :id: 76fdbb37-1b05-4f90-918e-d34e5e22ed7e
        """
        self.skipTest('Expected skip')
