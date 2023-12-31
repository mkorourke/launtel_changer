# launtel_changer
Mick's Launtel Speed Scripter

````
pip install --user -r ./requirements.txt
````

````
./mlss.py --help
usage: mlss.py [-h] [-p PSID] [-c] [-d]

Launtel Speed Info and Change CLI

options:
  -h, --help            show this help message and exit
  -p PSID, --psid PSID  Launtel Speed PSID
  -c, --commit          Commit to Launtel.
  -d, --debug           Debug logging to stderr.
````

Optional: Configure variables _USERNAME and or _PASSWORD with your Launtel login details, if not configured the script will interactively prompt for username or password which ever is not set. 

Use the -p option to define the Launtel PSID (or speed) specific to your discount or plan. If not set the script will display PSIDs available and interactively prompt.

The script is a dry-run by default, use the -c option to commit the speed change to Luantel.

Schedule with your preferred command scheduler.

> [!Note]
> Script is tested to support accounts with a single service, extra code would be neccessary to support accounts with multiple services.
