#!/usr/bin/env python

import argparse
import json
import csv

from lib.route_calc import RouteCalc

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate a routes file based on the passed in CSV file.')
  parser.add_argument('filename', type=str, help='the CSV file containing the orders')
  parser.add_argument('-c', '--config', type=file, help='the configuration filename')
  parser.add_argument('-v', '--verbose', action='store_true', help='increase the output verbosity')
  args = parser.parse_args()

  c = None
  d = []

  with args.config as json_data:
    c = json.load(json_data)
  c['verbose'] = args.verbose
  
  with open(args.filename, "rU") as data_file:
      for row in csv.DictReader(data_file):
        d.append(row)

  r = RouteCalc(c, d)
  r.route()
