# Delivery Routes

This program is used to calculate delivery routes given an origin (the materials depot from which all delivery trucks will leave), the number and types of trucks, and destinations. I wrote this for Herndon, VA's Troop 913 annual mulch fundraiser where we typically must deliver 6,000+ bags of mulch in a single (crazy) day.

## Requirements

* python 3.7
* pip3
* virtualenv
* webkit2png (can be installed via ```brew install webkit2png```)

### API Keys

You must obtain API keys (tokens) from [SmartyStreets](https://smartystreets.com/) and [Google Maps](https://cloud.google.com/maps-platform/maps/). They should be configured via the following environment variables:

* ```SMARTY_AUTH_ID```: The authentication identifier from SmartyStreets
* ```SMARTY_AUTH_TOKEN```: The authentication token from SmartyStreets
* ```GOOGLE_API_KEY```: The API key from Google Maps Platform

## Setup

Create a virtual environment, if you name it ```venv-delivery-routes``` in the top-level directory of this project, Git will ignore it. You can do that like so: ```python3 -m venv venv-delivery-routes```.

Source your virtual environment, like this: ```source venv-delivery-routes/bin/activate```, then run ```pip install -r venv_requirements.txt``` to pull down all of the dependencies.

## Running

The program requires a CSV as input with all of the order information (particularly the shipping addresses as per Shopify's CSV format).

The following command will output a routes.json file which should be used as input to the next stage:

```shell
$ ./router.py <orders.csv>
```

The following command will output one PDF file per route, based on the input ```routes.json``` file:

```shell
$ ./printer.py output/routes.json
```

NOTE: If you simply need to regenerate the PDF for a single route, you can specify the route number on the command-line like so:

```shell
$ ./printer.py output/routes.json 17
```

The following command allows you to regenerate the routes (```routes.json```), based on the input ```routes.csv``` file:

```shell
$ ./regen.py  -v -o output/orders.json output/routes.csv
```

This is useful when you want to hand-optimize the routes (you only need to make edits in the ```routes.csv``` file rather than mucking with the JSON file).

The following command will output a KML file for use with [Google My Maps](https://www.google.com/maps/d/). You can load it as follows:
1. Click on My Maps.
2. Click Create a new map.
3. Add a title and description.
4. Click Import.
5. Click Choose file, select the KML file to upload, and then click Upload from file.

```shell
$ ./gen_kml.py output/routes.json
```

### Configuration

The configuration file is a Python class with the following fields:

```json
class Config:
  def __init__(self):
    self.smarty_auth_id = environ['SMARTY_AUTH_ID']
    self.smarty_auth_token = environ['SMARTY_AUTH_TOKEN']
    self.google_api_key = environ['GOOGLE_API_KEY']
    self.trucks = [{ "type": "Box Truck", "capacity": 135 }, {"type": "26' Flatbed", "capacity": 315 }]
    self.contact = environ["CONTACT"]
    self.output_dir = "output"
    self.processes = 8
    self.origin = [38.950633, -77.397684]
    self.verbose = environ["VERBOSE"]
```

The fields are explained below:
* smarty_auth_id: This is the SmartyStreets auth ID -- only used to validate addresses (optional)
* smarty_auth_token: This is the SmartyStreets auth token -- only used to validate addresses (optional)
* google_api_key: This is the Google API key used to geocode addresses and map routes.
* trucks: This is the dictionary of trucks along with their capacity (in this case number of bags of mulch).
* contact: The contact information printed on the bottom of each delivery route (in case drivers need assistance).
* output_dir: The directory to write out all of the PDF files representing delivery routes.
* origin: The coordinates of the depot that all trucks start out from.
* verbose: Whether or not to print logging statements while processing the data.

## Overview

The algorithm used is extremely simple and doesn't always generate the best road-routes as it simply compares geographic coordinates (lat, lon). It also assumes that all of the items to deliver are uniform in size/weight (which is true for bags of mulch). Thus the capcity of the trucks and the orders is uniform--more work would be required if you wanted this to calculate delivery of differing items. 

This could be improved by using Google's routing API but to do so would require many different route computations which would exceed the free tier of usage, thus I haven't bothered. Instead, to improve the routes, I output an intermediate file, ```routes.json```, which can be hand-edited to improve routes and then passed in to the program to print out the PDF routes.
