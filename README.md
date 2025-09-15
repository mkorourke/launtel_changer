or# launtel_changer
Mick's Launtel Speed Scripter

````
pip install --user -r ./requirements.txt
````

````
./mlss.py --help
usage: mlss.py [-h] [-p PSID] [-c] [-l] [-d]

Launtel Speed Info and Change CLI

positional arguments:
  {shaper}              Available commands
    shaper              Shaper control options

options:
  -h, --help            show this help message and exit
  -p PSID, --psid PSID  Launtel Speed PSID
  -c, --commit          Commit to Launtel.
  -l, --latest          Use latest psid options.
  -d, --debug           Debug logging to stderr.

$ ./mlss.py shaper --help
usage: mlss.py shaper [-h] [--up UP] [--down DOWN]

options:
  -h, --help   show this help message and exit
  --up UP      Shaper upload, percentage of plan speed.
  --down DOWN  Shaper download, percentage of plan speed.
````

Optional: Configure variables _USERNAME and or _PASSWORD with your Launtel login details, if not configured the script will interactively prompt for username or password which ever is not set. 

Use the -p option to define the Launtel PSID (or speed) specific to your discount or plan. If not set the script will display PSIDs available and interactively prompt.

LAUNTEL_USERNAME and LAUNTEL_PASSWORD key-value pairs will be utlised if defined in a .env file.

The script is a dry-run by default, use the -c option to commit the speed change to Luantel. 

Schedule using -p and .env options with your preferred scheduler.

Use 'shape' option to view Launtel shaper information, using the '-c shaper' option will commit a shape change. Defaults to 108% down and 95% up.
Example:
````
./mlss.py -c shaper --up 108 --down 95
```

> [!Note]
> Script is tested to support accounts with a single service, extra code would be neccessary to support accounts with multiple services.

[Buy me a Coffee on BMC](https://www.buymeacoffee.com/mkorourke) [or Ko-Fi](https://ko-fi.com/mkorourke)
