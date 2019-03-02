#!/usr/bin/env python

import simplekml
import argparse
import colorsys
import numpy
import simplejson
import csv
import os

from lib.config import Config

def RGBToHTMLColor(rgb_tuple):
    """ convert an (R, G, B) tuple to #RRGGBB """
    hexcolor = '%02x%02x%02xff' % (int(rgb_tuple[0]*256), int(rgb_tuple[1]*256), int(rgb_tuple[2]*256))
    # that's it! '%02x' means zero-padded, 2-digit hex values
    return hexcolor

def get_colors(num_colors):
  colors=[]
  for i in numpy.arange(0., 360., 360. / num_colors):
      hue = i/360.
      lightness = (50 + numpy.random.rand() * 10)/100.
      saturation = (90 + numpy.random.rand() * 10)/100.
      colors.append(RGBToHTMLColor(colorsys.hls_to_rgb(hue, lightness, saturation)))
  return colors

def load_data(savefile):
  orders = {}

  with open(savefile, 'r') as json_data:
    try:
      orders = simplejson.load(json_data)
    except ValueError as e:
      print('invalid json: %s' % e)
      raise

  return orders

def save_routes_to_csv(config, routes):
  savefile = "{}/master.csv".format(config.output_dir)

  with open(savefile, "w") as csvfile:
    f = csv.writer(csvfile)

    # Write CSV Header, If you dont need that, remove this line
    f.writerow(["ID", "Name", "Address", "Bags", "Route", "Coments"])

    for idx, route in enumerate(routes):
      for d in route:
        f.writerow([d['id'], d['name'], d['address'], d['count'], "route-{}".format(idx+1), d['comments']])

  if config.verbose:
    print("Saved {} routes to {}".format(len(routes), savefile))

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate a KML file based on the passed in routes.json file.')
  parser.add_argument('filename', type=str, help='the routes.json file containing the deliveries')
  parser.add_argument('-v', '--verbose', action='store_true', help='increase the output verbosity')
  args = parser.parse_args()

  config = Config()
  config.verbose = args.verbose

  if not os.path.isfile(args.filename):
    print("There is no such file {}!".format(args.filename))
    sys.exit(-1)

  routes = load_data(args.filename)
  savefile = "{}/deliveries.kml".format(config.output_dir)

  if config.verbose:
    print("Loaded {} routes from {}".format(len(routes), args.filename))

  colors = get_colors(100)

  kml = simplekml.Kml(open=1)

  num_routes = 0
  num_orders = 0
  for idx, route in enumerate(routes):
    num_routes = idx + 1
    for delivery in route:
      pnt = kml.newpoint()
      pnt.name = "{} {} ({} bags)".format(delivery['id'], delivery['address'], delivery['count'])
      pnt.description = "route-{}".format(num_routes)
      pnt.coords = [(delivery['lon'], delivery['lat'])]
      pnt.style.iconstyle.color = colors[num_routes]
      pnt.style.iconstyle.icon.href = None
      num_orders = num_orders + 1

      if config.verbose:
        print("Added point for {} (route-{})".format(delivery['id'], num_routes))

  kml.save(savefile)
  if config.verbose:
    print("Created {} points, one per order.".format(num_orders))

  save_routes_to_csv(config, routes)
