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
_PASSWORD = '' # More ideally use a vault or password manager integration

_BASE_URL = 'https://residential.launtel.net.au'
_LOGIN_URL = f'{_BASE_URL}/login'
_SIGNOUT_URL = f'{_BASE_URL}/logout_user'
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
    '-l',
    '--latest',
    action='store_true',
    help='Use latest psid options.')
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

# get the arguments value for commit
if args.latest is True:
    logging.info('Use latest psid options is True.')
    _LATEST = True
else:
    logging.info('Use latest psid options is False.')
    _LATEST = False

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
LOGIN_STATUS = LOGIN_SOUP.find(
    'div', attrs={
        'class': 'alert-content'}).text.strip()

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

SERVICES_SOUP = BeautifulSoup(SERVICES, features='lxml')
SERVICES_STATUS = SERVICES_SOUP.find(
    'dl', attrs={'class': 'service-dl'}).text.strip()

if 'Active' in SERVICES_STATUS:
    logging.info('%s service status is Active.', _ISP)
else:
    logging.info('%s service status is not Active.', _ISP)


SERVICE_DETAILS_LINK = br.find_link(  # pylint: disable=assignment-from-none
    text='Show Advanced Info')
SERVICE_BASE_URL = SERVICE_DETAILS_LINK.base_url

MODIFY_SERVICE_URL = SERVICE_DETAILS_LINK.url.replace('service_details', 'service')
MODIFY_SERVICE_LINK = Link(
    base_url=SERVICE_BASE_URL,
    url=MODIFY_SERVICE_URL,
    text='Modify Service',
    tag='a',
    attrs=[
        ('href',
         MODIFY_SERVICE_URL)])
MODIFY_SERVICE = br.follow_link(MODIFY_SERVICE_LINK).read()
MODIFY_SERVICE_SOUP = BeautifulSoup(MODIFY_SERVICE, features='lxml')
logging.debug('url:%s', br.geturl())
br.select_form(name='manage_service')

LATEST_PSID_BTN=MODIFY_SERVICE_SOUP.find("button", {"onclick":"showLatest()"})
if LATEST_PSID_BTN is not None:
    logging.info('%s available', LATEST_PSID_BTN.text)
    LATEST_PSID_URL = f'{MODIFY_SERVICE_URL}&latest=1'
    LATEST_PSID_LINK = Link(
        base_url=SERVICE_BASE_URL,
        url=LATEST_PSID_URL,
        text='Show Latest Pricing Options',
        tag='a',
        attrs=[
            ('href',
            LATEST_PSID_URL)])
    if _LATEST is True:
        MODIFY_SERVICE = br.follow_link(LATEST_PSID_LINK).read()
        MODIFY_SERVICE_SOUP = BeautifulSoup(MODIFY_SERVICE, features='lxml')
        logging.debug('url:%s', br.geturl())
        br.select_form(name='manage_service')
else:
    logging.info('No latest psid options')

_USERID = MODIFY_SERVICE_SOUP.find('input', attrs={'name': 'userid'}).get('value')
_C_PSID = MODIFY_SERVICE_SOUP.find('input', attrs={'name': 'psid'}).get('value')
_UNPAUSE = MODIFY_SERVICE_SOUP.find('input', attrs={'name': 'unpause'}).get('value')
_SERVICE_ID = MODIFY_SERVICE_SOUP.find(
    'input', attrs={
        'name': 'service_id'}).get('value')
_UPGRADE_OPTIONS = MODIFY_SERVICE_SOUP.find(
    'input', attrs={'name': 'upgrade_options'}).get('value')
_DISCOUNT_CODE = ''  # /check_discount/0/{_AVCID}/
_AVCID = MODIFY_SERVICE_SOUP.find('input', attrs={'name': 'avcid'}).get('value')
_LOCID = MODIFY_SERVICE_SOUP.find('input', attrs={'name': 'locid'}).get('value')
_COAT = MODIFY_SERVICE_SOUP.find('input', attrs={'name': 'coat'}).get('value')
_PSID_VALID = False

SPEEDS = MODIFY_SERVICE_SOUP.find_all('span', attrs={'data-value': True})
for speed in SPEEDS:
    speed_psid = speed.get('data-value')
    if speed_psid == _C_PSID:
        speed_name = speed.find('div', attrs={'class': 'col-sm-4'}).text.strip()
        _C_TIER = speed_name
logging.info('Your speed psid:%s', _C_PSID)
logging.info('Your speed tier:%s', _C_TIER)  
for speed in SPEEDS:
    speed_name = speed.find('div', attrs={'class': 'col-sm-4'}).text.strip()
    speed_psid = speed.get('data-value')
    speed_daily_spend = speed.get('data-plancharge')
    print(f'psid={speed_psid},name={speed_name},daily_spend={speed_daily_spend}')

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
    CONFIRM = br.submit().read()
    logging.debug('url:%s', br.geturl())
    CONFIRM_SOUP = BeautifulSoup(CONFIRM, features='lxml')
    CONFIRM_STATUS = CONFIRM_SOUP.find(
        'dl', attrs={'class': 'service-dl'}).text.strip()
    if 'Change in progress' in CONFIRM_STATUS:
        logging.info('%s status is "Change in progress".', _ISP)
    else:
        logging.info(
            '%s status is not "Change in progress", please check portal.',
            _ISP)

logging.info('%s speed change script is complete, signing out.', _ISP)
SIGNOUT_LINK = Link(
    base_url=SERVICE_BASE_URL,
    url=_SIGNOUT_URL,
    text='Sign Out',
    tag='a',
    attrs=[
        ('href',
         _SIGNOUT_URL)])
br.follow_link(SIGNOUT_LINK)
logging.debug('url:%s', br.geturl())
