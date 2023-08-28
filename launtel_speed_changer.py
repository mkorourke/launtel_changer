#!/usr/bin/env python3
"""
Purpose: Module for Launtel Speed Info and Change via CLI
"""
import argparse
import getpass
import logging
import sys
from bs4 import BeautifulSoup
from mechanize import Browser
from mechanize import Link

_USERNAME = ''
_PASSWORD = ''

_BASE_URL = 'https://residential.launtel.net.au'
_LOGIN_URL = f'{_BASE_URL}/login'
_ISP = "Launtel"

def get_credentials(prompt):
    """
    Generic funtion to prompt for credentials
    """
    if sys.stdin.isatty():
        print(prompt)
        if _USERNAME == '':
            username = input('Username: ')
        else:
            username = _USERNAME
            print(f'Username: {username}')
        if _PASSWORD == '':
            password = getpass.getpass('Password: ')
        else:
            password = _PASSWORD
    else:
        if _USERNAME == '':
            username = sys.stdin.readline().rstrip()
        else:
            username = _USERNAME
            print(f'Username: {username}')
        if _PASSWORD == '':
            password = sys.stdin.readline().rstrip()
        else:
            password = _PASSWORD
    return [username, password]

parser = argparse.ArgumentParser(
    description='Launtel Speed Info and Change CLI')
# add arguments to the parser
parser.add_argument('-p', '--psid', help='Launtel Speed PSID')
parser.add_argument(
    '-c',
    '--commit',
    action='store_true',
    help=f'Commit to {_ISP}.')
parser.add_argument(
    '-d',
    '--debug',
    action='store_true',
    help='Debug logging to stderr.')

# parse the arguments
args = parser.parse_args()

if args.debug is True:
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logging.debug('Debug is True.')
else:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logger = logging.getLogger(__name__)

# get the arguments value for psid
if args.psid is not None:
    _PSID = args.psid
else:
    _PSID = ''

# get the arguments value for commit
if args.commit is True:
    logging.info('Commit is True.')
    _COMMIT = True
else:
    logging.info('Commit is False.')
    _COMMIT = False

# if not set, get the users credentials
if _USERNAME == '' or _PASSWORD == '':
    logging.info('%s username or password not set.', _ISP)
    _isp_credentials = get_credentials(f'Enter your {_ISP} credentials:')
    _USERNAME = _isp_credentials[0]
    _PASSWORD = _isp_credentials[1]

if _USERNAME == '' or _PASSWORD == '':
    logging.info('Quiting, %s username or password not set.', _ISP)
    sys.exit()

br = Browser()
br.set_handle_robots(False)   # ignore robots
br.set_handle_refresh(False)  # can sometimes hang without this
br.addheaders = [('User-agent', 'Firefox')]
br.open(_LOGIN_URL)
br.select_form(id='login-form')
br.form['username'] = _USERNAME
br.form['password'] = _PASSWORD
LOGIN = br.submit().read()  # pylint: disable=assignment-from-none
LOGIN_SOUP = BeautifulSoup(LOGIN, features='lxml')
LOGIN_STATUS = LOGIN_SOUP.find('div', attrs={'class': 'alert-content'}).text.strip()

if LOGIN_STATUS == 'Sorry incorrect login details':
    logging.info('Login Failure.')
    logging.debug('%s alert content : %s', _ISP, LOGIN_STATUS)
    sys.exit()
else:
    logging.info('Login Successful.')

COOKIES = br._ua_handlers['_cookies'].cookiejar  # pylint: disable=protected-access
for cookie in COOKIES:
    if cookie.name == "session_id":
        _SESSION_ID = cookie.value
        logging.debug('%s=%s', cookie.name, _SESSION_ID)

SERVICES = br.follow_link(text='Services').read()
logging.debug('url:%s', br.geturl())

SERVICE_DETAILS_LINK = br.find_link(  # pylint: disable=assignment-from-none
    text='Show Advanced Info')
SERVICE_BASE_URL = SERVICE_DETAILS_LINK.base_url
SERVICE_URL = SERVICE_DETAILS_LINK.url.replace('service_details', 'service')
SERVICE_LINK = Link(
    base_url=SERVICE_BASE_URL,
    url=SERVICE_URL,
    text='Modify Service',
    tag='a',
    attrs=[
        ('href',
         SERVICE_URL)])
SERVICE = br.follow_link(SERVICE_LINK).read()
SERVICE_SOUP = BeautifulSoup(SERVICE, features='lxml')
logging.debug('url:%s', br.geturl())
br.select_form(name='manage_service')

_USERID = SERVICE_SOUP.find('input', attrs={'name': 'userid'}).get('value')
_C_PSID = SERVICE_SOUP.find('input', attrs={'name': 'psid'}).get('value')
_UNPAUSE = SERVICE_SOUP.find('input', attrs={'name': 'unpause'}).get('value')
_SERVICE_ID = SERVICE_SOUP.find('input', attrs={'name': 'service_id'}).get('value')
_UPGRADE_OPTIONS = SERVICE_SOUP.find('input', attrs={'name': 'upgrade_options'}).get('value')
_DISCOUNT_CODE = '' # /check_discount/0/{_AVCID}/
_AVCID = SERVICE_SOUP.find('input', attrs={'name': 'avcid'}).get('value')
_LOCID = SERVICE_SOUP.find('input', attrs={'name': 'locid'}).get('value')
_COAT = SERVICE_SOUP.find('input', attrs={'name': 'coat'}).get('value')
_PSID_VALID = False

logging.info('Current psid:%s', _C_PSID)
SPEEDS = SERVICE_SOUP.find_all('span', attrs={'data-value': True})
for speed in SPEEDS:
    speed_name = speed.find('div', attrs={'class': 'col-sm-4'}).text.strip()
    speed_psid = speed.get('data-value')
    print(f'psid={speed_psid},name={speed_name}')

if _PSID == '':
    _PSID = input('Please enter psid: ')

for speed in SPEEDS:
    speed_name = speed.find('div', attrs={'class': 'col-sm-4'}).text.strip()
    speed_psid = speed.get('data-value')
    if _PSID == speed_psid:
        logging.info('Requested psid is valid.')
        _PSID_VALID = True

if _PSID_VALID is True:
    CONFIRM_SERVICE_BASE_URL = br.geturl()  # pylint: disable=assignment-from-none
    CONFIRM_SERVICE_URL = (f'/confirm_service?userid={_USERID}'
                           f'&psid={_PSID}&'
                           f'unpause={_UNPAUSE}&'
                           f'service_id={_SERVICE_ID}&'
                           f'upgrade_options={_UPGRADE_OPTIONS}&'
                           f'discount_code={_DISCOUNT_CODE}&'
                           f'avcid={_AVCID}&'
                           f'locid={_LOCID}&'
                           f'coat={_COAT}')
    CONFIRM_SERVICE_LINK = Link(
        base_url=CONFIRM_SERVICE_BASE_URL,
        url=CONFIRM_SERVICE_URL,
        text='Looks great - update it!',
        tag='a',
        attrs=[
            ('href',
             CONFIRM_SERVICE_URL)])
    CONFIRM_SERVICE = br.follow_link(CONFIRM_SERVICE_LINK).read()
    logging.debug('url:%s', br.geturl())
    CONFIRM_SERVICE_SOUP = BeautifulSoup(CONFIRM_SERVICE, features='lxml')
else:
    logging.info("Requested psid is not valid.")
    sys.exit()

if _COMMIT is True:
    br.select_form(name='confirm_service')
    br.submit()
    logging.debug('url:%s', br.geturl())
