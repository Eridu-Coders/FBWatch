#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX

import time
import re
import urllib.request
import sys

from lxml import html

# ---------------------------------------------------- Functions -------------------------------------------------------

# opens a Selenium driven Firefox window
def getDriver():
    # Create a new instance of the Firefox driver
    l_driver = webdriver.Firefox()

    # Resize the window to the screen width/height
    l_driver.set_window_size(1500, 1500)

    # Move the window to position x/y
    l_driver.set_window_position(1000, 1000)

    return l_driver

# get a unique text element through lxml, with a warning mark ('¤') inside the string
# inside the string if more than one was found
def getUnique(p_frag, p_xpath):
    return '¤'.join([str(l_span.text_content()) for l_span in p_frag.xpath(p_xpath)]).strip()

def loginAs(p_user, p_passwd):
    l_driver = getDriver()

    l_driver.get('http://localhost/FBWatch/FBWatchLogin.html')
    #l_driver.get('http://192.168.0.51/FBWatch/FBWatchLogin.html')

    try:
        l_status = WebDriverWait(l_driver, 15).until(EC.presence_of_element_located((By.ID, 'status')))

        # l_status = l_driver.find_element_by_id('status')
        while l_status.text != 'Please log into Facebook.':
            time.sleep(1)

        l_mainWindowHandle = None
        for l_handle in l_driver.window_handles:
            l_driver.switch_to.window(l_handle)
            print('Window: {0} {1}'.format(l_handle, l_driver.title))

            l_mainWindowHandle = l_handle

        l_button = l_driver.find_element_by_xpath('//span/iframe')

        l_src = l_button.get_attribute('src')
        l_content = urllib.request.urlopen(l_src).read().decode('utf-8').strip()

        # extract a full xml/html tree from the page
        l_tree = html.fromstring(l_content)

        l_buttonText = getUnique(l_tree, '//body')
        print('l_buttonText:', l_buttonText[0:50])

        if re.match('Log In', l_buttonText):
            time.sleep(2)
            l_button.click()
        else:
            print('Cannot log in')
            sys.exit()

        # Handle log-in pop-up
        l_finished = False
        while not l_finished:
            for l_handle in l_driver.window_handles:
                l_driver.switch_to.window(l_handle)
                print('Window: {0} {1}'.format(l_handle, l_driver.title))

                if l_driver.title == 'Facebook':
                    print('Found Login window')
                    l_finished = True

                    try:
                        # locate the user name (email) input box and enter the user name
                        l_user = WebDriverWait(l_driver, 10).until(EC.presence_of_element_located(
                            (By.ID, 'email')))
                        l_user.send_keys(p_user)

                        # locate the password input box and enter the apssword
                        l_pwd = l_driver.find_element_by_id('pass')
                        l_pwd.send_keys(p_passwd)

                        # submit the form
                        l_driver.find_element_by_id('loginbutton').click()
                    except EX.NoSuchElementException:
                        print('[01] Something is badly wrong (Element not found) ...')
                        return None, None
                    except EX.TimeoutException:
                        print('[02] Something is badly wrong (Timeout) ...')
                        return None, None

                    break

        # Handle permission pop-up if any or moves on after 10 s
        time.sleep(1)
        l_finished = False
        l_count = 0
        while not l_finished and l_count < 5:
            for l_handle in l_driver.window_handles:
                l_driver.switch_to.window(l_handle)
                print('Window: {0} {1}'.format(l_handle, l_driver.title))

                if l_driver.title == 'Log in with Facebook':
                    print('Found Permissions Window')

                    # Approve
                    l_driver.find_element_by_name('__CONFIRM__').click()

                    l_finished = True

            time.sleep(1)
            l_count += 1

        l_driver.switch_to.window(l_mainWindowHandle)

        # retrieve token value from the status line
        l_count = 0
        while len(l_status.text.split('|')) < 2:
            print('Waiting for status update', l_count)
            time.sleep(.1)
            l_count += 1
            if l_count >= 300:
                print('Could not retrieve token')
                sys.exit()

        l_accessToken = l_status.text.split('|')[1]

    except EX.TimeoutException:
        print('Did not find button')

        l_body = l_driver.find_element_by_xpath('//body').get_attribute('innerHTML')
        print(l_body)
        return None, None

    print('Sucessufully logged in as [{0}]'.format(p_user))

    return l_driver, l_accessToken

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Log-in as "X" on Facebook                                  |')
    print('|                                                            |')
    print('| v. 1.0 - 21/04/2016                                        |')
    print('+------------------------------------------------------------+')

    # l_driver = loginAs('kabir.eridu@gmail.com', '12Alhamdulillah')

    l_driver, l_accessToken = loginAs('john.braekernell@yahoo.com', '15Eyyaka')
    print('l_accessToken:', l_accessToken)
    l_driver.quit()

    l_driver, l_accessToken = loginAs('john.braekernell@yahoo.com', '15Eyyaka')
    print('l_accessToken:', l_accessToken)
    l_driver.quit()