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

    try:
        l_status = WebDriverWait(l_driver, 15).until(EC.presence_of_element_located((By.ID, 'status')))

        # l_status = l_driver.find_element_by_id('status')
        while l_status.text != 'Please log into Facebook.':
            time.sleep(1)

        l_button = l_driver.find_element_by_xpath('//span/iframe')

        l_src = l_button.get_attribute('src')
        l_content = urllib.request.urlopen(l_src).read().decode('utf-8').strip()

        # extract a full xml/html tree from the page
        l_tree = html.fromstring(l_content)

        l_buttonText = getUnique(l_tree, '//body')
        print('l_buttonText:', l_buttonText[0:50])

        if re.match('Log In', l_buttonText):
            l_button.click()

        l_finished = False
        while not l_finished:
            for l_handle in l_driver.window_handles:
                print('Handle:', l_handle)
                l_driver.switch_to.window(l_handle)
                print('title:', l_driver.title)

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
                        return 0
                    except EX.TimeoutException:
                        print('[02] Something is badly wrong (Timeout) ...')

                    break

    except EX.TimeoutException:
        print('Did not find button')

        l_body = l_driver.find_element_by_xpath('//body').get_attribute('innerHTML')
        print(l_body)
        return None

    print('Sucessufully logged in as [{0}]'.format(p_user))

    return l_driver

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Log-in as "X" on Facebook                                  |')
    print('|                                                            |')
    print('| v. 1.0 - 21/04/2016                                        |')
    print('+------------------------------------------------------------+')

    l_driver = loginAs('kabir.eridu@gmail.com', '12Alhamdulillah')

    #l_driver.quit()