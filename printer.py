#!/usr/bin/env python

from multiprocessing import Pool

import argparse
import datetime
import urllib
import json
import time
import csv
import sys
import os

from lib.config import Config
from lib.mypdf import MyFPDF

def print_routes(config, routes):
  # Process the routes to generate PDFs for the drivers
  bags       = 0
  deliveries = 0
  big_truck  = 0
  pool       = Pool(processes=config.processes)
  args       = [(config, "Route-{}".format(idx+1), d) for idx, d in enumerate(routes)]
  results    = pool.map(generate_pdf, args, 1)

  for res in results:
    bags += res[0]
    if res[0] > 135:
      big_truck += 1
    deliveries += res[1]

  # for a in args:
  #   b, d = generate_pdf(a)
  #   bags += b
  #   deliveries += d

  if config.verbose:
    print("{} bags delivered to {} addresses across {} routes ({} big truck routes).".format(bags, deliveries, len(routes), big_truck))

def generate_orders_csv(config, routes):
  """Generate a CSV with the following columsn: Order ID, Route, Name, Address, Bag Count, Comments"""
  savefile = "{}/orders.csv".format(config.output_dir)

  with open(savefile, "w") as csvfile:
    f = csv.writer(csvfile)

    # Write CSV Header, If you dont need that, remove this line
    f.writerow(["ID", "Route", "Name", "Address", "Bag Count", "Comments"])

    for idx, route in enumerate(routes):
      for d in route:
        f.writerow([d['id'], "route-{}".format(idx+1), d['name'], d['address'], d['count'], d['comments']])

  if config.verbose:
    print("Saved {} routes to {}".format(len(routes), savefile))

def generate_routes_csv(config, routes):
  """Generate a CSV with the following columns: Route, Order ID, Driver, Time Out, Time In, Duration"""
  savefile = "{}/routes.csv".format(config.output_dir)

  with open(savefile, "w") as csvfile:
    f = csv.writer(csvfile)

    # Write CSV Header, If you dont need that, remove this line
    f.writerow(["Route", "Bag Count", "Deliveries", "Stops", "Driver", "Time Out", "Time In", "Duration"])

    for idx, route in enumerate(routes):
      counter = 0
      deliveries = []
      for d in route:
        counter += int(d['count'])
        deliveries.append(d['id'])
      f.writerow(["route-{}".format(idx+1), counter, ";".join(deliveries), len(deliveries), "", "", "", ""])

  if config.verbose:
    print("Saved {} routes to {}".format(len(routes), savefile))

# private methods
def generate_pdf(arg):
  config = arg[0]
  title  = arg[1]
  r  = arg[2]

  if config.verbose:
    print("Working on {}/{}.pdf".format(config.output_dir, title))

  url  = url_for_route(r)
  bags = total_bags(r)
  deliveries = total_deliveries(r)
  os.system("webkit2png -D %s -o p%s -F -W 1440 -H 900 \"%s\" 1>&2 >/dev/null" % (config.output_dir, title, url))
  filename = "%s/p%s-full.png" % (config.output_dir, title)
  pdf = MyFPDF()
  pdf.set_margins(1.0, 0.5)
  pdf.add_page()
  pdf.write_html(gen_html(config, title, bags, r, filename))
  pdf.output("%s/%s.pdf" % (config.output_dir, title),'F')
  if config.verbose:
    print("Generated {}/{}.pdf".format(config.output_dir, title))
  return (bags, deliveries)

def total_bags(route):
  bags = 0
  for r in route:
    bags = bags + int(r['count'])
  return bags

def total_deliveries(route):
  return len(route)

def truck_type(config, count):
  for t in config.trucks:
    if count <= int(t['capacity']):
      return t['type']
  return "!INVALID!"

def gen_html(config, title, bags, r, img):
  truck = truck_type(config, bags)
  now = datetime.datetime.now()
  html = """
  <h1 align="center">%s (%s bags) %s</h1>
  <center>
  <img src="%s" width="480" height="320">
  </center>
  <ol>""" % (title, bags, truck, img)
  for order in r:
    notes = order['comments']
    html += "<li>%s (%s - <b>%s bags</b>)" % (order['address'], order['id'], order['count'])
    if notes and notes.strip():
      html += "<br/>%s" % (notes)
    html += "</li>"
  html += "</ol>"
  html += """<br /><hr />
  <ul>
    <li><b>Always set the parking brake before loading the vehicle</b></li>
    <li><b>Highlight each delivery after you've verified that the correct number of bags have been stacked.</b></li>
  </ul>
  <br /><hr />
  <center><b>For Support Call: %s</b></center><br />
  <center><small>%s</small></center>""" % (config.contact, now.strftime("%Y-%b-%d"))
  return html

def url_for_route(route):
  url = "https://maps.google.com/maps?f=d&mode=driving&source=s_d&saddr="
  for idx, order in enumerate(route):
    if idx == 0:
      url += urllib.parse.quote(order['address'])
      url += "&daddr="
    else:
      if idx != 1:
        url += "%20to:"
      url += urllib.parse.quote(order['address'])
  return url

def validate_routes(routes):
  seen_ids = {}
  for idx, route in enumerate(routes):
    for d in route:
      if int(d['origin_dist']) > 100:
        print("ERROR: Route-{} delivery {} is {} distance away from the origin!".format(idx, d['id'], d['origin_dist']))
        sys.exit(-1)
      if d['id'] in seen_ids:
        print("ERROR: Route-{} contains delivery {} which is also in Route-{}".format(idx, d['id'], seen_ids[d['id']]))
        sys.exit(-1)
      else:
        seen_ids[d['id']] = idx

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate PDF delivery routes based on the passed in routes file.')
  parser.add_argument('filename', type=str, help='the JSON file containing the routes to print')
  parser.add_argument('routeno', type=int, nargs='?', help='the route to print')
  parser.add_argument('-v', '--verbose', action='store_true', help='increase the output verbosity')  
  args = parser.parse_args()

  r = None
  c = Config()
  c.verbose = args.verbose

  if not os.path.isfile(args.filename):
    print("There is no such file {}!".format(args.filename))
    sys.exit(-1)

  with open(args.filename, 'r') as f:
    r = json.load(f)

  validate_routes(r)

  if args.routeno != None:
    if args.routeno > 0 and args.routeno <= len(r):
      generate_pdf([c, "Route-{}".format(args.routeno), r[args.routeno - 1]])
    else:
      print("ERROR: Invalid route number (max {})!".format(len(r)))
  else:
    print_routes(c, r)

  # Generate the master route list and order list for tracking progress
  generate_orders_csv(c, r)
  generate_routes_csv(c, r)
