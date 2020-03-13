#!/usr/bin/env python

import argparse
import json
import sys
import csv
import os

from lib.config import Config
from lib.route_calc import RouteCalc

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate a routes file based on the passed in CSV file.')
  parser.add_argument('filename', type=str, help='the CSV file containing the orders')
  parser.add_argument('-v', '--verbose', action='store_true', help='increase the output verbosity')
  args = parser.parse_args()

  d = []
  
  if not os.path.isfile(args.filename):
    print("There is no such file {}!".format(args.filename))
    sys.exit(-1)

  with open(args.filename, mode="r", encoding="utf-8-sig") as data_file:
    for row in csv.DictReader(data_file):
      d.append(row)

  c = Config()
  c.verbose = args.verbose
  r = RouteCalc(c)
  r.load_csv(d)
  rval = r.route()
  sys.exit(rval)