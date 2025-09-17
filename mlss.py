#!/usr/bin/env python3
"""
Purpose: Script for Launtel Speed Info and Change
"""
import argparse
import getpass
import logging
import sys
import signal
import os
import re
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import parse_qs
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from mechanize import Browser
from mechanize import Link
from rich import box
from rich.table import Table
from rich.console import Console

_USERNAME = ''
_PASSWORD = ''

_BASE_URL = 'https://residential.launtel.net.au'
_LOGIN_URL = f'{_BASE_URL}/login'
_SIGNOUT_URL = f'{_BASE_URL}/logout_user'
_MODIFY_SERVICE_URL = f'{_BASE_URL}/service'
_ISP = "Launtel"
_LOGIN_SUCCESSFUL = False
_COMPLETE = False

_COMMIT = False
_LATEST = False
_SHAPER = False
_PSID_VALID = False
_PSID = ''
_UP = ''
_DOWN = ''

_SHAPER_DICT = {}
_SERVICE_DICT = {}
_SPEEDS_DICT = {}
_USERID = ''
_AVCID = ''
_C_PSID = ''
_UNPAUSE = ''
_SERVICE_ID = ''
_UPGRADE_OPTIONS = ''
_DISCOUNT_CODE = ''
_LOCID = ''
_COAT = ''


def signal_handler(sig, frame):
    """
    Capture Ctrl+C and logout if login was successful
    """
    logging.debug('Signal captured: sig: %s frame: %s', sig, frame)
    print('\nYou pressed Ctrl-C, Quiting.')
    if _LOGIN_SUCCESSFUL:
        logout()
    else:
        sys.exit(0)


def create_parser():
    """
    Arg Parser
    """
    parser = argparse.ArgumentParser(
        description='Launtel Speed Info and Change CLI',
        add_help=True
    )

    # Add main arguments
    parser.add_argument('-p', '--psid', help='Launtel Speed PSID')
    parser.add_argument(
        '-c',
        '--commit',
        action='store_true',
        help=f'Commit to {_ISP}.'
    )
    parser.add_argument(
        '-l',
        '--latest',
        action='store_true',
        help='Use latest PSID options'
    )
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help='Debug logging to stderr'
    )

    # Add subparser for shaper command
    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')
    parser_shaper = subparsers.add_parser(
        'shaper', help='Shaper control options')
    parser_shaper.add_argument(
        '--up',
        default=95,
        type=int,
        help='Shaper upload, percentage of plan speed.'
    )
    parser_shaper.add_argument(
        '--down',
        default=108,
        type=int,
        help='Shaper download, percentage of plan speed.'
    )

    return parser


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


def get_browser():
    """
    Create _browser and set desired defaults
    """
    browser = Browser()
    browser.set_handle_robots(False)   # ignore robots
    browser.set_handle_refresh(False)  # can sometimes hang without this
    browser.addheaders = [('User-agent', 'Firefox')]
    return browser


def logout():
    """
    Logout of Launtel
    """
    if _SHAPER is True:
        logging.info(
            '%s shaper change complete status is %s, signing out.',
            _ISP, _COMPLETE)
    else:
        logging.info(
            '%s speed change complete status is %s, signing out.',
            _ISP, _COMPLETE)
    _br.follow_link(Link(
        base_url=_BASE_URL,
        url=_SIGNOUT_URL,
        text='Sign Out',
        tag='a',
        attrs=[
            ('href',
             _SIGNOUT_URL)]))
    logging.debug('url:%s', _br.geturl())
    sys.exit()


def login():
    """
    Login to Launtel
    """
    _br.open(_LOGIN_URL)
    _br.select_form(id='login-form')
    _br.form['username'] = _USERNAME
    _br.form['password'] = _PASSWORD
    _login_soup = BeautifulSoup(_br.submit().read(), features='lxml')
    _login_status = _login_soup.find(
        'div', attrs={
            'class': 'alert-content'}).text.strip()
    if _login_status == 'Sorry incorrect login details':
        logging.error('Login Failure.')
        logging.debug('%s alert content : %s', _ISP, _login_status)
        sys.exit()
    logging.debug('Login Successful.')
    return True


def check_latest(_latest_psid_btn):
    """
    Check latest pricing options exist
    """
    if _latest_psid_btn is not None:
        logging.debug('%s available', _latest_psid_btn.text)
        return True
    logging.debug('No latest psid options')
    return False


def submit_service_modification():
    """
    Prepare the service modification URL and submit modification confirmation if Commit is True
    """
    _confirm_service_url = (f'/confirm_service?userid={_USERID}'
                            f'&psid={_PSID}&'
                            f'unpause={_UNPAUSE}&'
                            f'service_id={_SERVICE_ID}&'
                            f'upgrade_options={_UPGRADE_OPTIONS}&'
                            f'discount_code={_DISCOUNT_CODE}&'
                            f'avcid={_AVCID}&'
                            f'locid={_LOCID}&'
                            f'coat={_COAT}',
                            f'churn={_CHURN}')
    _confirm_service_link = Link(
        base_url=_BASE_URL,
        url=_confirm_service_url,
        text='Looks great - update it!',
        tag='a',
        attrs=[
            ('href',
             _confirm_service_url)])
    _br.follow_link(_confirm_service_link)
    logging.debug('url:%s', _br.geturl())
    if _COMMIT is True:
        _br.select_form(name='confirm_service')
        _confirm_soup = BeautifulSoup(_br.submit().read(), features='lxml')
        logging.debug('url:%s', _br.geturl())
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


def get_queue_type(soup):
    """
    Get active shaper queue type
    """
    queue_types = ['shape', 'police']
    for q_type in queue_types:
        attrs = {'name': 'queue_type', 'value': q_type}
        if soup.find('input', attrs=attrs).get('checked') is not None:
            return q_type
    return None


def get_shaper_control_option(soup, control_name, options):
    """
    Get shaper control options
    """
    for option in options:
        attrs = {'name': control_name, 'id': f'{control_name}_{option}'}
        if soup.find('input', attrs=attrs).get('checked') is not None:
            return option
    return None


def get_shaper_input_attribute(soup, input_id, attribute):
    """
    Get attribute from input element.
    """
    return soup.find('input', attrs={'id': input_id}).get(attribute)


def get_shaper_control(_br):
    """
    Get shaper control info
    """
    soup = BeautifulSoup(_br.follow_link(
        text='Show Advanced Info'), features='lxml')
    logging.debug('url:%s', _br.geturl())

    queue_type = get_queue_type(soup)
    shaperdown_control = get_shaper_control_option(
        soup, 'shaperdown_control', ['none', 'default', 'override'])
    shaperup_control = get_shaper_control_option(
        soup, 'shaperup_control', ['none', 'default', 'override'])

    shaperdown_speed = 'override'  # always override to keep this simple
    shaperup_speed = 'override'

    shaperdown_max = get_shaper_input_attribute(soup, 'shaperdown_speed', 'max')
    shaperdown_min = get_shaper_input_attribute(soup, 'shaperdown_speed', 'min')
    shaperdown_speed_value = get_shaper_input_attribute(
        soup, 'shaperdown_speed', 'value')

    shaperup_max = get_shaper_input_attribute(soup, 'shaperup_speed', 'max')
    shaperup_min = get_shaper_input_attribute(soup, 'shaperup_speed', 'min')
    shaperup_speed_value = get_shaper_input_attribute(soup, 'shaperup_speed', 'value')

    shaper_control_url = soup.find(
        'form', attrs={'name': 'form-shaping'}).get('action')

    shaper_dict = {
        'queue_type': queue_type,
        'shaperdown_cont': shaperdown_speed,
        'shaperdown_control': shaperdown_control,
        'shaperdown_speed': shaperdown_speed_value,
        'shaperup_cont': shaperup_speed,
        'shaperup_control': shaperup_control,
        'shaperup_speed': shaperup_speed_value,
        'shaperdown_max': shaperdown_max,
        'shaperdown_min': shaperdown_min,
        'shaperup_max': shaperup_max,
        'shaperup_min': shaperup_min,
        'shaper_control_url': shaper_control_url,
    }

    return shaper_dict


def get_shaper_table(_title):
    """
    Create a new shaper table
    """
    table = Table(
        show_header=True,
        header_style='bold magenta',
        title=_title,
        box=box.SQUARE,
        show_lines=True)
    table.add_column('Name')
    table.add_column('Value')
    return table


def print_shaper_table(_up, _down):
    """
    Get the shaper table
    """
    _shaper_title = f'{_ISP} Shaper Control'
    _shaper_table = get_shaper_table(_shaper_title)
    _shaper_table.add_row(*('Queue Type', _SHAPER_DICT["queue_type"]))
    _shaper_table.add_row(
        *('Down Control', _SHAPER_DICT["shaperdown_control"]))
    _shaper_table.add_row(*('Down Max', _SHAPER_DICT["shaperdown_max"]))
    _shaper_table.add_row(*('Down Min', _SHAPER_DICT["shaperdown_min"]))
    _shaper_table.add_row(*('[bright_green]Down Value[/bright_green]',
                          f'[bright_green]{_SHAPER_DICT["shaperdown_speed"]}[/bright_green]'))
    if _COMMIT is True:
        _shaper_table.add_row(
            *('[bright_yellow]Down Commit[/bright_yellow]', f'[bright_yellow]{_down}[/bright_yellow]'))
    _shaper_table.add_row(*('Up Control', _SHAPER_DICT["shaperup_control"]))
    _shaper_table.add_row(*('Up Max', _SHAPER_DICT["shaperup_max"]))
    _shaper_table.add_row(*('Up Min', _SHAPER_DICT["shaperup_min"]))
    _shaper_table.add_row(*('[bright_green]Up Value[/bright_green]',
                          f'[bright_green]{_SHAPER_DICT["shaperup_speed"]}[/bright_green]'))
    if _COMMIT is True:
        _shaper_table.add_row(
            *('[bright_yellow]Up Commit[/bright_yellow]', f'[bright_yellow]{_up}[/bright_yellow]'))
    _console = Console()
    _console.print(_shaper_table)


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
    table.add_column('NTD UPGRADE')
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
    for _key, _values in _SPEEDS_DICT.items():
        _speed_psid = _key
        _speed_name = _values['name']
        _speed_daily_spend = _values['spend']
        _ntdupgrade = bool(int(_values['ntdupgrade']))
        if _key == _C_PSID and _LATEST is False:
            _speed_psid = f'[bright_green]{_speed_psid}[/bright_green]'
            _speed_name = f'[bright_green]{_speed_name}[/bright_green]'
            _speed_daily_spend = f'[bright_green]{_speed_daily_spend}[/bright_green]'
            _ntdupgrade= f'[bright_green]{_ntdupgrade}[/bright_green]'
        elif _key == _C_PSID:
            _speed_name = f'[bright_yellow]{_speed_name}[/bright_yellow]'
            _speed_name = f'[bright_yellow]{_speed_name}[/bright_yellow]'
            _speed_daily_spend = f'[bright_yellow]{_speed_daily_spend}[/bright_yellow]'
            _ntdupgrade= f'[bright_yellow]{_ntdupgrade}[/bright_yellow]'
        _speeds_table.add_row(*(_speed_psid, _speed_name, _speed_daily_spend, str(_ntdupgrade)))

    _console = Console()
    _console.print(_speeds_table)


def get_speeds_dict(soup):
    """
    Get a dict of speeds sorted by spend
    """
    _speeds = soup.find_all(
        'span', attrs={'data-value': True})
    _speeds_dict = {}

    for speed in _speeds:
        _speed_name = speed.find(
            'div', attrs={
                'class': 'col-sm-4'}).text.strip()
        _speed_psid = speed.get('data-value')
        _speed_daily_spend = speed.get('data-plancharge')
        _speed_ntdupgrade = speed.get('data-ntdupgrade')
        _speeds_dict[_speed_psid] = {
            'name': _speed_name.replace('\t', '').replace('\n', '').replace('[1]', ''),
            'spend': _speed_daily_spend,
            'ntdupgrade': _speed_ntdupgrade,
        }
    # Sort the dictionary by spend value
    _sorted_speeds_dict = dict(
        sorted(_speeds_dict.items(), key=lambda x: x[1]['spend'])
    )

    return _sorted_speeds_dict


def get_service_dict(soup):
    """
    Get a dict of the service
    """
    # Find all the values utilised within Launtels service modification
    # and necessary for next services of validations and script steps
    _userid = soup.find(
        'input', attrs={'name': 'userid'}).get('value')
    _c_psid = soup.find(
        'input', attrs={'name': 'psid'}).get('value')
    _unpause = soup.find(
        'input', attrs={'name': 'unpause'}).get('value')
    _service_id = soup.find(
        'input', attrs={
            'name': 'service_id'}).get('value')
    _upgrade_options = soup.find(
        'span', attrs={'class': 'rollover list-group-item'}).get('value')
    _discount_code = ''  # /check_discount/0/{_AVCID}/
    _avcid = soup.find(
        'input', attrs={'name': 'avcid'}).get('value')
    _locid = soup.find(
        'input', attrs={'name': 'locid'}).get('value')
    _coat = soup.find('input', attrs={'name': 'coat'}).get('value')
    _churn = soup.find('input', attrs={'name': 'coat'}).get('value')

    _service_dict = {}
    _service_dict[_avcid] = {
        'userid': _userid,
        'psid': _c_psid,
        'unpause': _unpause,
        'service_id': _service_id,
        'upgrade_options': _upgrade_options,
        'discount_code': _discount_code,
        'locid': _locid,
        'coat': _coat,
        'churn': _churn}

    return _service_dict


def print_active_service_status():
    """
    Check active service status
    """
    _services_soup = BeautifulSoup(
        _br.follow_link(
            text='Services').read(),
        features='lxml')
    logging.debug('url:%s', _br.geturl())
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


signal.signal(signal.SIGINT, signal_handler)
# parse the arguments
_parser = create_parser()
args = _parser.parse_args()

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

# get the arguments value for commit
if args.commit is True:
    logging.debug('Commit is True.')
    _COMMIT = True
else:
    logging.debug('Commit is False.')

# get the arguments value for commit
if args.latest is True:
    logging.debug('Use latest psid options is True.')
    _LATEST = True
else:
    logging.debug('Use latest psid options is False.')

# get the arguments value for commit
if args.command == 'shaper':
    logging.debug('Shaper control is True.')
    _SHAPER = True
    _UP = int(args.up)
    _DOWN = int(args.down)
else:
    logging.debug('Shaper control is False.')


# Load variables from .env file
load_dotenv()
# Check and utilise ENV variables for user credentials
if os.getenv("LAUNTEL_USERNAME") is not None:
    _USERNAME = os.getenv("LAUNTEL_USERNAME")
if os.getenv("LAUNTEL_PASSWORD") is not None:
    _PASSWORD = os.getenv("LAUNTEL_PASSWORD")

# if ENV not set, interactivly prompt for user credentials
if _USERNAME == '' or _PASSWORD == '':
    logging.debug('%s username or password not set.', _ISP)
    _isp_credentials = get_credentials(f'Enter your {_ISP} credentials:')
    _USERNAME = _isp_credentials[0]
    _PASSWORD = _isp_credentials[1]

if _USERNAME == '' or _PASSWORD == '':
    logging.error('Quiting, %s username or password not set.', _ISP)
    sys.exit()

_br = get_browser()
_LOGIN_SUCCESSFUL = login()
if args.debug is True:
    print_cookies()
    print_active_service_status()
# Make sure we are at the correct starting point
_br.follow_link(text='Services')
logging.debug('url:%s', _br.geturl())
parsed_url = urlparse(_br.find_link(text='Show Advanced Info').url)
_USERID = parse_qs(parsed_url.query)['userid'][0]
_AVCID = parse_qs(parsed_url.query)['avcid'][0]
_MODIFY_SERVICE_URL = f'{_MODIFY_SERVICE_URL}?avcid={_AVCID}&userid={_USERID}'
_soup = BeautifulSoup(
    _br.follow_link(Link(
        base_url=_BASE_URL,
        url=_MODIFY_SERVICE_URL,
        text='Modify Service',
        tag='a',
        attrs=[
            ('href',
             _MODIFY_SERVICE_URL)])).read(),
    features='lxml')
logging.debug('url:%s', _br.geturl())
_br.select_form(name='manage_service')

# Check if new pricing or plan options exist
if _LATEST is True and check_latest(
    _soup.find(
        "button", {
            "onclick": "showLatest()"})) is True:
    _LATEST_PSID_URL = f'{_MODIFY_SERVICE_URL}&latest=1'
    _soup = BeautifulSoup(
        _br.follow_link(Link(
            base_url=_BASE_URL,
            url=_LATEST_PSID_URL,
            text='Show Latest Pricing Options',
            tag='a',
            attrs=[
                ('href',
                 _LATEST_PSID_URL)])).read(),
        features='lxml')
    logging.debug('url:%s', _br.geturl())
    _br.select_form(name='manage_service')

# Get a dict with all the service information
_SERVICE_DICT = get_service_dict(_soup)
# Set the remaining required variables
_C_PSID = _SERVICE_DICT[_AVCID]['psid']
_UNPAUSE = _SERVICE_DICT[_AVCID]['unpause']
_SERVICE_ID = _SERVICE_DICT[_AVCID]['service_id']
_UPGRADE_OPTIONS = _SERVICE_DICT[_AVCID]['upgrade_options']
_DISCOUNT_CODE = _SERVICE_DICT[_AVCID]['discount_code']
_LOCID = _SERVICE_DICT[_AVCID]['locid']
_COAT = _SERVICE_DICT[_AVCID]['coat']
_CHURN = _SERVICE_DICT[_AVCID]['coat']
# Get speeds and print
_SPEEDS_DICT = get_speeds_dict(_soup)

if _SHAPER is True:
    _br.follow_link(text='Services')
    _SHAPERUP_SPEED = ''
    _SHAPERDOWN_SPEED = ''
    for _key, values in _SPEEDS_DICT.items():
        if _key == _C_PSID:
            _speed_name = values['name']
            pattern = re.escape('(') + "(.*?)" + re.escape(')')
            _speed_plan = re.findall(pattern, _speed_name)
            _speed_plan = _speed_plan[0].split('/')
            _SHAPERDOWN_SPEED = int(int(_speed_plan[0]) * (_DOWN/100))
            _SHAPERUP_SPEED = int(int(_speed_plan[1]) * (_UP/100))
    _SHAPER_DICT = get_shaper_control(_br)
    if int(_SHAPER_DICT["shaperup_min"]) <= _SHAPERUP_SPEED <= int(_SHAPER_DICT["shaperup_max"]):
        logging.debug('Up Commit %s is valid.', _SHAPERUP_SPEED)
    else:
        logging.error('Up Commit %s is not valid.', _SHAPERUP_SPEED)
        _COMPLETE = False
        logout()
    if int(_SHAPER_DICT["shaperdown_min"]) <= _SHAPERDOWN_SPEED <= int(_SHAPER_DICT["shaperdown_max"]):
        logging.debug('Down Commit %s is valid.', _SHAPERDOWN_SPEED)
    else:
        logging.error('Down Commit %s is not valid.', _SHAPERDOWN_SPEED)
        _COMPLETE = False
        logout()
    print_shaper_table(_SHAPERUP_SPEED, _SHAPERDOWN_SPEED)
    _SHAPER_CONTROL_URL = _BASE_URL + _SHAPER_DICT["shaper_control_url"]
    if _COMMIT is True:
        # Define _SHAPER_CONTROL_DATA as a dictionary directly
        _SHAPER_CONTROL_DICT = {
            "queue_type": _SHAPER_DICT["queue_type"],
            "shaperdown_cont": _SHAPER_DICT["shaperdown_control"],
            "shaperdown_control": _SHAPER_DICT["shaperdown_control"],
            "shaperdown_speed": _SHAPERDOWN_SPEED,
            "shaperup_cont": _SHAPER_DICT["shaperup_control"],
            "shaperup_control": _SHAPER_DICT["shaperup_control"],
            "shaperup_speed": _SHAPERUP_SPEED
        }
        # URL-encode the form data and Post
        _br.open(_SHAPER_CONTROL_URL, urlencode(_SHAPER_CONTROL_DICT))
        _COMPLETE = True  # If we get to here Complete is considered True
        logout()
    else:
        _COMPLETE = False
        logout()

print_speeds_table()
# check and cater for non-interactive eg. cron based entry of PSID
if _PSID != '':
    _PSID_VALID = check_psid()
    # if non-interactive PSID is false, logout
    if _PSID_VALID is False:
        logout()

# check and cater for interactive entry of PSID, re-prompt if PSID is invalid
while _PSID_VALID is False:
    _PSID = input('Please enter psid: ')
    _PSID_VALID = check_psid()

if _PSID_VALID is True:
    submit_service_modification()
else:
    logging.error("Requested psid is not valid.")
    logout()

_COMPLETE = True  # If we get to here Complete is considered True
logout()
