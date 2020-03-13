#!/usr/bin/env python

import argparse
import json
import sys
import csv
import os

from lib.config import Config
from lib.route_calc import RouteCalc

def generate_routes_csv(config, routes):
  """Generate a CSV with the following columns: Route, Order ID, Driver, Time Out, Time In, Duration"""
  savefile = "{}/routes.csv".format(config.output_dir)

  with open(savefile, "w") as csvfile:
    f = csv.writer(csvfile)
    num_orders = 0
    # Write CSV Header, If you dont need that, remove this line
    f.writerow(["Route", "Bag Count", "Deliveries", "Stops", "Driver", "Time Out", "Time In", "Duration"])
    validate_deliveries = {}

    for idx, route in enumerate(routes):
      counter = 0
      deliveries = []
      for d in route:
        counter += int(d['count'])
        deliveries.append(d['id'])
        if d['id'] in validate_deliveries:
          print("ERROR: order {} appears in multiple deliveries!".format(d['id']))
        else:
          validate_deliveries[d['id']] = 1
        num_orders += 1
      f.writerow(["route-{}".format(idx+1), counter, ";".join(deliveries), len(deliveries), "", "", "", ""])

  if config.verbose:
    print("Saved {} routes with {} orders to {}".format(len(routes), num_orders, savefile))

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Re-generate a routes file based on the passed in CSV file.')
  parser.add_argument('filename', type=str, help='the CSV file containing the routes')
  parser.add_argument('-o', '--orders', help='the orders.json file')
  parser.add_argument('-v', '--verbose', action='store_true', help='increase the output verbosity')
  args = parser.parse_args()

  c = Config()
  c.verbose = args.verbose
  delivery_routes = []
  
  if not os.path.isfile(args.filename):
    print("There is no such file {}!".format(args.filename))
    sys.exit(-1)

  if not os.path.isfile(args.orders):
    print("There is no such file {}!".format(args.orders))

  r = RouteCalc(c)
  r.load_json(args.orders)

  with open(args.filename, mode="r", encoding="utf-8-sig") as data_file:
    for row in csv.DictReader(data_file):
      d = row['Deliveries'].split(';')
      delivery_routes.append(d)

  routes = r.expand_routes(delivery_routes)
  r.save_routes(routes)
  generate_routes_csv(c, routes)
