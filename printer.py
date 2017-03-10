#!/usr/bin/env python

from multiprocessing import Pool

import argparse
import urllib
import json
import time
import os

from lib.mypdf import MyFPDF

def print_routes(config, routes):
  # Process the routes to generate PDFs for the drivers
  bags       = 0
  deliveries = 0
  big_truck  = 0
  pool       = Pool(processes=config['processes'])
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

  if config['verbose']:
    print "{} bags delivered to {} addresses across {} routes ({} big truck routes).".format(bags, deliveries, len(routes), big_truck)

# private methods
def generate_pdf(arg):
  config = arg[0]
  title  = arg[1]
  r  = arg[2]

  if config['verbose']:
    print "Working on {}/{}.pdf".format(config['output_dir'], title)

  url  = url_for_route(r)
  bags = total_bags(r)
  deliveries = total_deliveries(r)
  os.system("webkit2png -D %s -o p%s -F -W 1440 -H 900 \"%s\" 1>&2 >/dev/null" % (config['output_dir'], title, url))
  filename = "%s/p%s-full.png" % (config['output_dir'], title)
  pdf = MyFPDF()
  pdf.set_margins(1, 0.5, 1)
  pdf.add_page()
  pdf.write_html(gen_html(config, title, bags, r, filename))
  pdf.output("%s/%s.pdf" % (config['output_dir'], title),'F')
  if config['verbose']:
    print "Generated {}/{}.pdf".format(config['output_dir'], title)
  return (bags, deliveries)

def total_bags(route):
  bags = 0
  for r in route:
    bags = bags + int(r['count'])
  return bags

def total_deliveries(route):
  return len(route)

def truck_type(config, count):
  for t in config['trucks']:
    if count <= int(t['capacity']):
      return t['type']
  return "!INVALID!"

def gen_html(config, title, bags, r, img):
  truck = truck_type(config, bags)
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
  <br />
  <p><center><b>For Support Call: %s</b></center></p>""" % (config['contact'])
  return html

def url_for_route(route):
  url = "https://maps.google.com/maps?f=d&mode=driving&source=s_d&saddr="
  for idx, order in enumerate(route):
    if idx == 0:
      url += urllib.quote_plus(order['address'])
      url += "&daddr="
    else:
      if idx != 1:
        url += "%20to:"
      url += urllib.quote_plus(order['address'])
  return url

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate PDF delivery routes based on the passed in routes file.')
  parser.add_argument('filename', type=file, help='the JSON file containing the routes to print')
  parser.add_argument('routeno', type=int, nargs='?', help='the route to print')
  parser.add_argument('-c', '--config', type=file, help='the configuration filename')
  parser.add_argument('-v', '--verbose', action='store_true', help='increase the output verbosity')  
  args = parser.parse_args()

  c = None
  r = None

  with args.config as json_data:
    c = json.load(json_data)
    c['verbose'] = args.verbose

  with args.filename as json_data:
    r = json.load(json_data)

  if args.routeno != None:
    if args.routeno > 0 and args.routeno < len(r):
      generate_pdf([c, "Route-{}".format(args.routeno), r[args.routeno - 1]])
    else:
      print "ERROR: Invalid route number (max {})!".format(len(r))
  else:
    print_routes(c, r)
