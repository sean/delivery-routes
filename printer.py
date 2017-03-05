#!/usr/bin/env python

import argparse
import urllib
import json
import os

from lib.mypdf import MyFPDF

class Printer:

  def __init__(self, config, routes):
    self.config = config
    self.routes = routes

  def print_routes(self):
    # Process the routes to generate PDFs for the drivers
    num_routes = 0
    for idx, d in enumerate(self.routes):
      num_routes = idx + 1
      self.generate_pdf("Route-%d" % (num_routes), d)

  # private methods
  def generate_pdf(self, title, r):
    url  = self.url_for_route(r)
    bags = self.total_bags(r)
    os.system("webkit2png -D %s -o p%s -F -W 1440 -H 900 \"%s\" 1>&2 >/dev/null" % (self.config['output_dir'], title, url))
    filename = "%s/p%s-full.png" % (self.config['output_dir'], title)
    pdf = MyFPDF()
    pdf.add_page()
    pdf.write_html(self.gen_html(title, bags, r, filename))
    pdf.output("%s/%s.pdf" % (self.config['output_dir'], title),'F')
    # print title,"(",bags,"):",url

  def total_bags(self, route):
    bags = 0
    for r in route:
      bags = bags + int(r['count'])
    return bags

  def truck_type(self, count):
    for t in self.config['trucks']:
      if count < int(t['capacity']):
        return t['type']
    return "!INVALID!"

  def gen_html(self, title, bags, r, img):
    truck = self.truck_type(bags)
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
      <li><b>Highlight each delivery after you've verified that the correct number of bags have been stacked.</li>
      <li><b>Return this sheet once all deliveries have been highlighted.</li>
    </ul>
    <br />
    <p><center><b>For Support Call: %s</b></center></p>""" % (self.config['contact'])
    return html

  def url_for_route(self, route):
    url = "https://maps.google.com/maps?f=d&source=s_d&saddr="
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

  p = Printer(c, r)
  p.print_routes()
