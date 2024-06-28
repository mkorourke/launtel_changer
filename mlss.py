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
from rich import box
from rich.table import Table
from rich.console import Console

_USERNAME = ''
_PASSWORD = '' # More ideally use a vault or password manager integration

_BASE_URL = 'https://residential.launtel.net.au'
_LOGIN_URL = f'{_BASE_URL}/login'
_SIGNOUT_URL = f'{_BASE_URL}/logout_user'
_ISP = "Launtel"

def get_speeds_table(_title):
    """
    Create a new speeds table
    """
    table = Table(
        show_header=True,
        header_style='bold magenta',
        title=_title,
        box=box.SQUARE,
        show_lines=True)
    table.add_column('PSID')
    table.add_column('SPEED')
    table.add_column('SPEND')
    return table

def add_speeds_table_row(
        _table,
        _psid,
        _speed_name,
        _daily_spend):
    """
    Add a row to a speeds table
    """
    _table.add_row(*(_psid, _speed_name, _daily_spend))
    return _table

def print_table(_table):
    """
    Print a table
    """
    _console = Console()
    _console.print(_table)

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
    logging.debug('Commit is True.')
    _COMMIT = True
else:
    logging.debug('Commit is False.')
    _COMMIT = False

# get the arguments value for commit
if args.latest is True:
    logging.debug('Use latest psid options is True.')
    _LATEST = True
else:
    logging.debug('Use latest psid options is False.')
    _LATEST = False

# if not set, get the users credentials
if _USERNAME == '' or _PASSWORD == '':
    logging.debug('%s username or password not set.', _ISP)
    _isp_credentials = get_credentials(f'Enter your {_ISP} credentials:')
    _USERNAME = _isp_credentials[0]
    _PASSWORD = _isp_credentials[1]

if _USERNAME == '' or _PASSWORD == '':
    logging.error('Quiting, %s username or password not set.', _ISP)
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
    logging.error('Login Failure.')
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
    logging.debug('%s service status is Active.', _ISP)
else:
    logging.error('%s service status is not Active.', _ISP)


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
    logging.debug('%s available', LATEST_PSID_BTN.text)
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
    logging.debug('No latest psid options')

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

if _LATEST is True:
    SPEEDS_TITLE = f'Latest {_ISP} Speeds'
else:
    SPEEDS_TITLE = f'{_ISP} Speeds'

SPEEDS_TABLE = get_speeds_table(SPEEDS_TITLE)
SPEEDS = MODIFY_SERVICE_SOUP.find_all('span', attrs={'data-value': True})
_SPEEDS_DICT = {}

for speed in SPEEDS:
    speed_name = speed.find('div', attrs={'class': 'col-sm-4'}).text.strip()
    speed_psid = speed.get('data-value')
    speed_daily_spend = speed.get('data-plancharge')
    _SPEEDS_DICT[speed_psid] = {'name': speed_name, 'spend': speed_daily_spend}

for key, values in _SPEEDS_DICT.items():
    speed_psid = key
    speed_name = values['name']
    speed_daily_spend = values['spend']
    if key == _C_PSID and _LATEST is False:
        _C_TIER = values['name']
        speed_psid = f'[bright_green]{speed_psid}[/bright_green]'
        speed_name = f'[bright_green]{speed_name}[/bright_green]'
        speed_daily_spend = f'[bright_green]{speed_daily_spend}[/bright_green]'
    elif key == _C_PSID:
        _C_TIER = values['name']
        speed_psid = f'[bright_yellow]{speed_psid}[/bright_yellow]'
        speed_name = f'[bright_yellow]{speed_name}[/bright_yellow]'
        speed_daily_spend = f'[bright_yellow]{speed_daily_spend}[/bright_yellow]'
    SPEEDS_TABLE = add_speeds_table_row(SPEEDS_TABLE,speed_psid,speed_name,speed_daily_spend)

print_table(SPEEDS_TABLE)

if _PSID == '':
    _PSID = input('Please enter psid: ')

for key in _SPEEDS_DICT:
    if _PSID == key:
        if _PSID == _C_PSID and _LATEST is False:
            logging.error("Requested psid is not valid.")
            sys.exit()
        else:
            logging.debug('Requested psid is valid.')
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
    logging.error("Requested psid is not valid.")
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
        logging.error(
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
