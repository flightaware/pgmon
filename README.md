# PGMON #


`PGMON` is a small daemon written in python that maintains a persistent connection to a postgresql database and periodically queries it for stats/performance data.  It can send that data to external systems for monitoring/alerting purposes.  By default, it is configured to use zabbix with zabbix_sender to get the data out, but you could write a module to send the data anywere in any format you'd like.  It also comes with support for writing the data in json format to a file or via HTTP POST/PUT to a webservice. The queries to run and what to do with the results are stored in a config file so you don't need to rewrite the app just to add new monitoring capabilities.  The config file is in a json format so it is easy to edit, parse, and even generate programmatically if you want.

## Changes ##

#### v1.0.0 ####
1. Initial Public Release

## Requirements ##

* OS: Linux or FreeBSD are the only ones supported at the moment, though anywhere python will run could work in theory 
* Python: version 3.4+ works. It also works with v2.7; however, the sha-bang line has been changed to default to python3, if found
* Database: For connecting to postgres (the only supported DB at the moment) psycopg2 is required.  
* Destinations: For the zabbix destination, zabbix_sender (usually part of the zabbix agent package on most systems) must be installed.  

## Install Process ##
1. Ensure psycopg2 is installed via `pip3 install psycopg2`
2. Ensure the zabbix_sender program is installed via your OSes preferred package manager
2. Run the `./configure.sh` script to determine your python path and what OS (Linux or FreeBSD) you're on.  It will use os-specific applications to add the 'pgmon' user and group, which is the only reason it cares.
3. Run `sudo make install` to put the library in the standard place (/usr/local/pgmon/lib) and the main program in the standard place (/usr/local/bin/pgmon)
4. Create /usr/local/pgmon/etc/pgmon.conf. A pgmon.conf.sample is available in the same dir to get you started

## Running Pgmon ##
You can run pgmon from the command line as `pgmon -c /usr/local/pgmon/etc/pgmon.conf`.  If you have it configured to switch to another user and you don't have the ability to do that, you'll probably need to run it as a user who does (eg root).

### FreeBSD ###
For FreeBSD systems, there is an included rc script.  Assuming you've got `pgmon_enabled="YES"` in your rc.conf, you can do `[sudo] service pgmon start`.

### Linux ###
On linux there is a systemd unit file.  You can do `[sudo] systemctl start pgmon`

### Docker ###
You need to mount the directory where the configuration file lives.  Otherwise, its pretty much just a standard docker run
`docker run -d -h $(hostname) --name=pgmon --net=host --mount 'type=bind,src=/usr/local/flightaware/etc/pgmon/pgmon_<hostname>.conf,dst=/usr/local/pgmon/etc/pgmon.conf,readonly' pgmon`

## Config File Format ##

The config file is a json object with a top level name of "Config".  Beneath that are four required sections with a number of sub-elements that may or may not be required.  If they've got a (Default *), then they aren't required, otherwise, they are.  

1. Pgmon - Configures the application itself
	a. PidFile - Location of the pidfile (Default: /var/run/pgmon/pgmon.pid)
	b. User - Username to run pgmon as (Default: pgmon)
	c. Group - Group to run pgmon as (Default: pgmon)
	d. CheckInterval - Period of time (in seconds) to wait before checking again (Default: 60)
	e. Daemon - Whether or not to daemonize.  1 means yes, 2 means no (Default 1)
2. Database - Parameters for the database you want to monitor
	a. Name - Name of the database you want to monitor
	b. Type - The type of database you want to monitor.  Currently, the only valid option is "Postgres"
	c. Host - The hostname/IP of the database you want to monitor
	d. Port - The port to connect to
	e. Username - The database user to connect as
	f. Password - the password to use for the connection
3. Destinations - Where to send the results.
	a. Name - Something descriptive to identify the destination.  Can be any valid string, but you've got to reference it in the item section, so its probably best to not go too crazy
	b. Type - What kind of destination you want to use.  This corresponds to the package name in the `destinations` package.  
	c. <Type Specific Values> - Each Type may have 1 more more options that can go here.  View the section for the type to learn more
4. Items - The specific queries you want to run
	a. Query - The sql query to run.  Note that only the first row is returned, so make sure the data you want is in that first row
	b. Destination - The name of the destination to send the results to.  Can also be an array of destination names.
	c. Id - An identifier for this item.  Must be unique in the configuration.  Will be combined with the column name and sent along with the value to the destination
	d. MultiRow - Whether or not this query contains multiple rows of values.  Must be set to the name of the column whose value will be used to build the item key in combination with `Id`

### Example Config: ###
```
{
    "Config": {
        "Pgmon": {
            "PidFile":"/var/run/pgmon.pid",
            "User":"pgmon",
            "Group":"pgmon",
            "CheckInterval":60,
            "Daemon":1
        },
        "Database": {
            "Name":"pgdata",
            "Type":"Postgres",
            "Host":"db.domain.com",
            "Port":5432,
            "Username":"pgsql",
            "Password":"mypass"}
        "Destinations": [
            {"Name":"Zabbix",
             "Type":"application.zabbix",
             "Host":"zabbix.domain.com",
             "Port":10051
            },
            {"Name":"www",
             "Type":"net.http",
             "Location":"https://domain.com/pgmon_endpoint",
             "PostVariable":"pgmon",
             "Format":"json"
            }
        ],
        "Items": [
            {"Query":"SELECT count(1) as count from table",
             "Destination":"Zabbix",
             "Id":"postgres.table"
            },
            {"Query":"SELECT sum(bytes) as total_bytes from stats_table",
             "Destination":"www",
             "Id":"postgres.stats_table"
            },
            {"Query":"SELECT count(1) as num_items from table2",
             "Destination":["Zabbix","www"],
             "Id":"postgres.table2"
            },
            {"Query":"select sum(xact_commit) as committed, sum(xact_rollback) as rollback from pg_stat_database",
             "Destination":"Zabbix",
             "Id":"postgres.transactions"
            },
            {"Query":"select sum(tup_updated) as updated, sum(tup_returned) as returned, sum(tup_inserted) as inserted, sum(tup_fetched) as fetched, sum(tup_deleted) as deleted FROM pg_stat_database",
             "Destination":"www",
             "Id":"postgres.tuples"
            },
            {"Query":"select client_addr, extract(epoch from replay_lag) as lag_ms from pg_stat_replication",
             "Destination":"www",
             "Id":"postgres.replication_delay",
             "MultiRow": "client_addr"
            }
		]
    }
}
```


##Item identification##

`PGMON` will combine with item Id with the column names so that each value can be uniquely identified. In the example configuration above, we are aliasing some of the computed columns to give them a more friendly name. If you don't do this, you may end up with wonky item Ids: 
`postgres.tuples.sum(tup_updated)`

If you specify an item as a `MultiRow` item, you need to identify a column that will be used to construct the id so each row can be uniquely identified.  See the `MultiRow` section below for more details.

## MultiRow ##

MultiRow allows you to perform a single query and get results across multiple rows.  This is useful if you have a table that holds stats for multiple things of the same kind.  For example, if you wanted to get the replication latency for SR backends from pg_stat_replication.

You set the configuration of MultiItem to be the name of the column to use for building the item key.  `PGMON` will build the key by combining the `Id` configuration item with the value in the specified column for each row.  So if you have a table that looks like this:
```
      username    |   login_count    
------------------+----------------
 bob              | 10
 sally            | 11
 jane             | 3
```

and the configuration has 

```
{ "Query": "select username, login_count from table",
  "Destination": "MyDest",
  "Id": "login.count",
  "MultiItem": "username"
}
```

Then your item keys will end up like `login.count.bob`, `login.count.sally`, etc etc.

Note that how these keys get built when sending to a specific destination may be different as, for example, zabbix will require values in a different format than the http module.

## Destinations ##
Info about the available destinations.

### application.zabbix ###
This destination uses zabbix_sender to send items to a zabbix server.  The items must be configured as a type "Zabbix Trapper".  `PGMON` will send the configured item Id as the zabbix item id, a unix timestamp when the value was collected, and the raw value itself.  In the destination config you can chose the hostname the checks are for so you don't have to run `PGMON` on the host you are monitoring.

#### Configuration Items ####
1. Server - The hostname of the zabbix server to send the checks to
2. Host - The name of the host the checks are for.  Must match what is configured in zabbix. (Default: local host's fqdn)
3. Port - The port on the zabbix server to connect to for sending zabbix trapper items (Default: 10051)
4. SenderLocation - The path to the `zabbix_sender` binary.  (Default: /usr/bin/zabbix_sender)

### net.http ###
This destination will send an HTTP GET/POST to a web endpoint.  The data can be formatted in a number of ways (extensible), but the default is json

#### Configuration Items ####
1. Location - HTTP(S) URL that will receive the data
2. Format - How the submitted data should be formatted.  Currently valid options are `json` or `csv` (Default: json)
3. Verb - The HTTP verb to use.  Eg GET or POST (Default: POST)
4. PostVariable - The GET or POST variable to set all the data to
5. Persist - Whether to keep the connection persistently, or reconnect for each delivery.  (Default: false)

### file.jsonfile ###
This destination outputs a file in json format containing the item id, a unix timestamp from when the value was collected, and the raw value itself.

#### Configuration Items ####
1. Location - The path and filename for where to write the results to.  Must be writable by the user `PGMON` runs as, obviously
2. Append - Whether or not to append the latest values to the file or overwrite.  1 will append, 0 will not. (Default: 0)

