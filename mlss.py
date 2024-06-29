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
_PASSWORD = ''  # More ideally use a vault or password manager integration

_BASE_URL = 'https://residential.launtel.net.au'
_LOGIN_URL = f'{_BASE_URL}/login'
_SIGNOUT_URL = f'{_BASE_URL}/logout_user'
_ISP = "Launtel"
_COMPLETE = False


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


def logout():
    """
    Logout of Launtel
    """
    if _COMPLETE is True:
        logging.info(
            '%s speed change script status is complete, signing out.',
            _ISP)
    else:
        logging.info('%s speed change script status error, signing out.', _ISP)

    signout_link = Link(
        base_url=SERVICE_BASE_URL,
        url=_SIGNOUT_URL,
        text='Sign Out',
        tag='a',
        attrs=[
            ('href',
             _SIGNOUT_URL)])
    _br.follow_link(signout_link)
    logging.debug('url:%s', _br.geturl())
    sys.exit()


def confirm_service_modification():
    """
    Confirm the service modification and submit if confirm is True
    """
    _confirm_service_base_url = _br.geturl()  # pylint: disable=assignment-from-none
    _confirm_service_url = (f'/confirm_service?userid={_USERID}'
                            f'&psid={_PSID}&'
                            f'unpause={_UNPAUSE}&'
                            f'service_id={_SERVICE_ID}&'
                            f'upgrade_options={_UPGRADE_OPTIONS}&'
                            f'discount_code={_DISCOUNT_CODE}&'
                            f'avcid={_AVCID}&'
                            f'locid={_LOCID}&'
                            f'coat={_COAT}')
    _confirm_service_link = Link(
        base_url=_confirm_service_base_url,
        url=_confirm_service_url,
        text='Looks great - update it!',
        tag='a',
        attrs=[
            ('href',
             _confirm_service_url)])
    _br.follow_link(_confirm_service_link).read()
    logging.debug('url:%s', _br.geturl())
    if _COMMIT is True:
        _br.select_form(name='confirm_service')
        _confirm = _br.submit().read()
        logging.debug('url:%s', _br.geturl())
        _confirm_soup = BeautifulSoup(_confirm, features='lxml')
        _confirm_status = _confirm_soup.find(
            'dl', attrs={'class': 'service-dl'}).text.strip()
        if 'Change in progress' in _confirm_status:
            logging.info('%s status is "Change in progress".', _ISP)
        else:
            logging.error(
                '%s status is not "Change in progress", please check portal.',
                _ISP)
            logout()


def check_psid():
    """
    Return True if the PSID is valid
    """
    _psid_valid = False
    for _key in _SPEEDS_DICT:
        if _PSID == _key:
            if _PSID == _C_PSID and _LATEST is False:
                logging.error("Requested psid is not valid.")
            else:
                logging.debug('Requested psid is valid.')
                _psid_valid = True
    return _psid_valid


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


def print_speeds_table():
    """
    Get the speeds table
    """
    if _LATEST is True:
        _speeds_title = f'Latest {_ISP} Speeds'
    else:
        _speeds_title = f'{_ISP} Speeds'
    _speeds_table = get_speeds_table(_speeds_title)
    for _key, values in _SPEEDS_DICT.items():
        speed_psid = _key
        speed_name = values['name']
        speed_daily_spend = values['spend']
        if _key == _C_PSID and _LATEST is False:
            speed_psid = f'[bright_green]{speed_psid}[/bright_green]'
            speed_name = f'[bright_green]{speed_name}[/bright_green]'
            speed_daily_spend = f'[bright_green]{speed_daily_spend}[/bright_green]'
        elif _key == _C_PSID:
            speed_psid = f'[bright_yellow]{speed_psid}[/bright_yellow]'
            speed_name = f'[bright_yellow]{speed_name}[/bright_yellow]'
            speed_daily_spend = f'[bright_yellow]{speed_daily_spend}[/bright_yellow]'
        _speeds_table.add_row(*(speed_psid, speed_name, speed_daily_spend))

    _console = Console()
    _console.print(_speeds_table)


def get_speeds_dict(_modify_services_soup):
    """
    Get a dict of speeds
    """
    _speeds = _modify_services_soup.find_all(
        'span', attrs={'data-value': True})
    _speeds_dict = {}

    for speed in _speeds:
        speed_name = speed.find(
            'div', attrs={
                'class': 'col-sm-4'}).text.strip()
        speed_psid = speed.get('data-value')
        speed_daily_spend = speed.get('data-plancharge')
        _speeds_dict[speed_psid] = {
            'name': speed_name,
            'spend': speed_daily_spend}

    return _speeds_dict


def print_active_service_status():
    """
    Check active service status
    """
    _services = _br.follow_link(text='Services').read()
    logging.debug('url:%s', _br.geturl())

    _services_soup = BeautifulSoup(_services, features='lxml')
    _services_status = _services_soup.find(
        'dl', attrs={'class': 'service-dl'}).text.strip()

    if 'Active' in _services_status:
        logging.debug('%s service status is Active.', _ISP)
    else:
        logging.debug('%s service status is not Active.', _ISP)


def print_cookies():
    """
    Print _browser session_id cookie
    """
    _cookies = _br._ua_handlers['_cookies'].cookiejar  # pylint: disable=protected-access
    for cookie in _cookies:
        if cookie.name == "session_id":
            _session_id = cookie.value
            logging.debug('%s=%s', cookie.name, _session_id)


def get_browser():
    """
    Create _browser and set desired defaults
    """
    __br = Browser()
    __br.set_handle_robots(False)   # ignore robots
    __br.set_handle_refresh(False)  # can sometimes hang without this
    __br.addheaders = [('User-agent', 'Firefox')]
    return __br


def login():
    """
    Login to Launtel
    """
    _br.open(_LOGIN_URL)
    _br.select_form(id='login-form')
    _br.form['username'] = _USERNAME
    _br.form['password'] = _PASSWORD
    _login = _br.submit().read()  # pylint: disable=assignment-from-none
    _login_soup = BeautifulSoup(_login, features='lxml')
    _login_status = _login_soup.find(
        'div', attrs={
            'class': 'alert-content'}).text.strip()

    if _login_status == 'Sorry incorrect login details':
        logging.error('Login Failure.')
        logging.debug('%s alert content : %s', _ISP, _login_status)
        sys.exit()
    else:
        logging.debug('Login Successful.')


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

_br = get_browser()
login()
if args.debug is True:
    print_cookies()
    print_active_service_status()


#Make sure we are at the correct starting point
_br.follow_link(text='Services').read()
logging.debug('url:%s', _br.geturl())
# A hack for the moment to short-cut post login landing method of finding avcid
# and userid values to then create a URL to mirror the Modify Service JS button with Mechanize
SERVICE_DETAILS_LINK = _br.find_link(  # pylint: disable=assignment-from-none
    text='Show Advanced Info')
SERVICE_BASE_URL = SERVICE_DETAILS_LINK.base_url
MODIFY_SERVICE_URL = SERVICE_DETAILS_LINK.url.replace(
    'service_details', 'service')
MODIFY_SERVICE_LINK = Link(
    base_url=SERVICE_BASE_URL,
    url=MODIFY_SERVICE_URL,
    text='Modify Service',
    tag='a',
    attrs=[
        ('href',
         MODIFY_SERVICE_URL)])
MODIFY_SERVICE = _br.follow_link(MODIFY_SERVICE_LINK).read()
MODIFY_SERVICE_SOUP = BeautifulSoup(MODIFY_SERVICE, features='lxml')
logging.debug('url:%s', _br.geturl())
_br.select_form(name='manage_service')

# Check if new pricing or plan options exist
LATEST_PSID_BTN = MODIFY_SERVICE_SOUP.find(
    "button", {"onclick": "showLatest()"})
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
        MODIFY_SERVICE = _br.follow_link(LATEST_PSID_LINK).read()
        MODIFY_SERVICE_SOUP = BeautifulSoup(MODIFY_SERVICE, features='lxml')
        logging.debug('url:%s', _br.geturl())
        _br.select_form(name='manage_service')
else:
    logging.debug('No latest psid options')

# Find all the values utilised within Launtels service modification
# and necessary for next services of validations and script steps
_USERID = MODIFY_SERVICE_SOUP.find(
    'input', attrs={'name': 'userid'}).get('value')
_C_PSID = MODIFY_SERVICE_SOUP.find(
    'input', attrs={'name': 'psid'}).get('value')
_UNPAUSE = MODIFY_SERVICE_SOUP.find(
    'input', attrs={'name': 'unpause'}).get('value')
_SERVICE_ID = MODIFY_SERVICE_SOUP.find(
    'input', attrs={
        'name': 'service_id'}).get('value')
_UPGRADE_OPTIONS = MODIFY_SERVICE_SOUP.find(
    'input', attrs={'name': 'upgrade_options'}).get('value')
_DISCOUNT_CODE = ''  # /check_discount/0/{_AVCID}/
_AVCID = MODIFY_SERVICE_SOUP.find(
    'input', attrs={'name': 'avcid'}).get('value')
_LOCID = MODIFY_SERVICE_SOUP.find(
    'input', attrs={'name': 'locid'}).get('value')
_COAT = MODIFY_SERVICE_SOUP.find('input', attrs={'name': 'coat'}).get('value')

# Get speeds and print
_SPEEDS_DICT = get_speeds_dict(MODIFY_SERVICE_SOUP)
print_speeds_table()

if _PSID == '':
    _PSID = input('Please enter psid: ')

_PSID_VALID = check_psid()
while _PSID_VALID is False:
    _PSID = input('Please enter psid: ')
    _PSID_VALID = check_psid()

if _PSID_VALID is True:
    confirm_service_modification()
else:
    logging.error("Requested psid is not valid.")
    logout()

_COMPLETE = True
logout()
