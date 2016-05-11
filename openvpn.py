#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

from subprocess import Popen, PIPE
import re
import time
import urllib.request
import urllib.error
from threading  import Thread
from queue import Queue, Empty  # python 3.x
import sys
import os
# ---------------------------------------------------- Functions -------------------------------------------------------

# Calls a "what is my Ip" web service to get own IP
def getOwnIp():
    # http://icanhazip.com/
    l_myIp = None
    try:
        l_myIp = urllib.request.urlopen('http://icanhazip.com/').read().decode('utf-8').strip()
    except urllib.error.URLError as e:
        print('Cannot Open http://icanhazip.com/ service:', repr(e))

    # https://ipapi.co/ip/
    if l_myIp is None:
        try:
            l_myIp = urllib.request.urlopen('https://ipapi.co/ip/').read().decode('utf-8').strip()
        except urllib.error.URLError as e:
            print('Cannot Open https://ipapi.co/ip/ service:', repr(e))

    return l_myIp

# turns on Openvpn with the config file given in parameter
# returns a process
# If alive --> everything ok
# if dead (poll() not None) --> error of some kind
def switchonVpn(p_config, p_verbose=True):
    if os.geteuid() != 0:
        print('Must be root')
        sys.exit()

    # function to output lines as a queue
    # (1) from http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
    def enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    # print IP before openvpn switches on if in verbose mode
    if p_verbose:
        print('Old Ip:', getOwnIp())

    # records starting time to be able to time out if takes too long
    t0 = time.perf_counter()

    # calls openvpn
    ON_POSIX = 'posix' in sys.builtin_module_names
    l_process = Popen(['openvpn', p_config],
                      stdout=PIPE,
                      stderr=PIPE,
                      cwd='/etc/openvpn',
                      bufsize=1,
                      universal_newlines=True,
                      close_fds=ON_POSIX)

    # see (1) above
    l_outputQueue = Queue()
    t = Thread(target=enqueue_output, args=(l_process.stdout, l_outputQueue))
    t.daemon = True  # thread dies with the program
    t.start()

    # wait for openvpn to establish connection
    while True:
        # cancels process if openvpn closes unexpectedly or takes more than 30 seconds to connect
        if l_process.poll() is not None or time.perf_counter() - t0 > 30.0:
            l_out = l_process.stdout.readline().strip()
            l_err = l_process.stderr.readline().strip()
            print('+++', l_out)
            print('---', l_err)

            # kills process if still running
            if l_process.poll() is not None:
                l_process.kill()

            break

        # l_out = l_process.stdout.readline().strip()

        # read line without blocking
        try:
            l_out = l_outputQueue.get_nowait().strip()  # or q.get(timeout=.1)
        except Empty:
            time.sleep(.1)
        else:  # got line
            # prints openvpn output if in verbose mode
            if p_verbose:
                print('+++', l_out)

            # if "Initialization Sequence Completed" appears in message --> connexion established
            if re.search('Initialization Sequence Completed', l_out):
                if p_verbose:
                    print('OpenVpn pid :', l_process.pid)
                    # print new IP
                    print('New Ip      :', getOwnIp())
                    print('Elapsed time:', time.perf_counter() - t0, 'seconds')

                break

    return l_process

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Openvpn driver script                                      |')
    print('|                                                            |')
    print('| v. 1.0 - 20/04/2016                                        |')
    print('+------------------------------------------------------------+')

    # TorGuard.United.Kingdom.ovpn
    l_process = switchonVpn('TorGuard.United.Kingdom.ovpn', p_verbose=True)
    #l_process = switchonVpn('TorGuard.South.Africa.ovpn', p_verbose=True)
    #l_process = switchonVpn('TorGuard.Swiss.ovpn', p_verbose=True)

    if l_process.poll() is None:
        l_process.kill()

    print('Ip now:', getOwnIp())