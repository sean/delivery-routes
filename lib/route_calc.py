from geopy.distance import great_circle
from collections import OrderedDict
from operator import itemgetter

import googlemaps
import os.path
import json

class Container(object):
  pass

class ContainerEncoder(json.JSONEncoder):
  def default(self, obj):
    return obj.__dict__

class RouteCalc:
  def __init__(self, config, data):
    self.config = config
    self.client = googlemaps.Client(self.config['api_key'])
    # This must appear last as it uses both config and client
    self.data   = self.validate_data(data)

  def route(self):
    # calculate the adjacencies (between each delivery address) if needed
    adjacencies = self.load_adjacencies()
    if len(adjacencies) != len(self.data):
      adjacencies = self.calculate_adjacencies()

    # Used to keep track of orders already in delivery plan
    planned_deliveries = []
    # Used to hold each of the delivery routes
    delivery_routes = []

    # Sort the orders by origin_dist, farthest to closest
    orders = sorted(self.data.items(), key=lambda x: x[1].origin_dist)

    # Now that each adjacency list is ordered, let's work through the deliveries
    for k in reversed(orders):
      k = k[0]
      if k in planned_deliveries: continue

      route = self.chunk_deliveries(k, adjacencies, planned_deliveries)

      delivery_routes.append(route)
      planned_deliveries.extend(route)

    self.save_routes(self.expand_routes(delivery_routes))

  # private methods

  def validate_data(self, data):
    orders = {}
    loaded_orders = self.load_orders()
    for address in data:
      if len(address['NAME']) > 0 and len(address['ADDRESS'].strip()) > 0:
        entry = Container()
        entry.id = address['BD ID']
        entry.name = address['NAME']
        entry.address = "{}, {}, VA {}".format(address['ADDRESS'].strip(), address['TOWN'].strip(), address['ZIP'].strip())
        entry.count = address['BAGS']
        entry.comments = address['COMMENTS']

        if entry.count == 0:
          print "ERROR: Order {} contains 0 items!".format(entry.id)
    
        # avoid expensive calculations by reusing the data from the loaded orders
        if entry.id in loaded_orders:
          entry.lat = loaded_orders[entry.id]['lat']
          entry.lon = loaded_orders[entry.id]['lon']
          entry.origin_dist = loaded_orders[entry.id]['origin_dist']
        else:
          (entry.lat, entry.lon) = self.geocode(entry.address)
          entry.origin_dist = great_circle((self.config['origin'][0], self.config['origin'][1]), (entry.lat,entry.lon)).miles
    
        orders[entry.id] = entry
      else:
        print "ERROR: Bad entry in input: {}".format(address['BD ID'])

    self.save_orders(orders)

    return orders

  def chunk_deliveries(self, id, adjacencies, planned_deliveries):
    route = [id]

    # TODO: Fix this to determine the best type of truck for the order
    count = 135 - int(self.data[id].count)

    if count < 0:
      print "ERROR: Order {} is {} items, which won't fit on one truck!".format(id, self.data[id].count)

    for n in adjacencies[id]:
      if n[1] > 3: break
      if n[0] in planned_deliveries: continue
      if n[0] in route: continue
      if (count - int(self.data[n[0]].count)) >= 0:
        route.append(n[0])
        count = count - int(self.data[n[0]].count)

    return route

  def expand_routes(self, routes):
    expanded_routes = []

    for route in routes:
      r = []
      for id in route:
        r.append(self.data[id])
      expanded_routes.append(r)

    return expanded_routes

  def calculate_adjacencies(self):
    if self.config['verbose']:
      print "Calculating adjacencies"
    adjacencies = {}

    for k,v in self.data.iteritems():
      if not k in adjacencies:
        adjacencies[k] = {}
      for l,w in self.data.iteritems():
        if l == k: continue
        adjacencies[k][l] = great_circle((v.lat, v.lon), (w.lat, w.lon)).miles

    # Now that we've calculated all of the adjacencies, let's order them by distance
    for a in adjacencies:
      adjacencies[a] = sorted(adjacencies[a].items(), key=itemgetter(1))

    self.save_adjacencies(adjacencies)

    return adjacencies

  def load_adjacencies(self):
    adjacencies = {}
    savefile = "{}/adjacencies.json".format(self.config['output_dir'])

    if os.path.isfile(savefile): 
      with open(savefile, 'r') as json_data:
        adjacencies = json.load(json_data)

    if self.config['verbose']:
      print "Loaded {} adjacencies from {}".format(len(adjacencies), savefile)

    return adjacencies

  def save_adjacencies(self, data):
    savefile = "{}/adjacencies.json".format(self.config['output_dir'])

    with open(savefile, 'w') as f:
      json.dump(data, f, indent=2, cls=ContainerEncoder)

    if self.config['verbose']:
      print "Saved {} adjacencies to {}".format(len(data), savefile)    

  def load_orders(self):
    orders = {}
    savefile = "{}/orders.json".format(self.config['output_dir'])

    if os.path.isfile(savefile): 
      with open(savefile, 'r') as json_data:
        orders = json.load(json_data)

    if self.config['verbose']:
      print "Loaded {} orders from {}".format(len(orders), savefile)

    return orders

  def save_orders(self, data):
    savefile = "{}/orders.json".format(self.config['output_dir'])

    with open(savefile, 'w') as f:
      json.dump(data, f, indent=2, cls=ContainerEncoder)

    if self.config['verbose']:
      print "Saved {} orders to {}".format(len(data), savefile)

  def save_routes(self, routes):
    savefile = "{}/routes.json".format(self.config['output_dir'])

    with open(savefile, 'w') as f:
      json.dump(routes, f, indent=2, cls=ContainerEncoder)

    if self.config['verbose']:
      print "Saved {} routes to {}".format(len(routes), savefile)

  def geocode(self, addr):
    if self.config['verbose']:
      print "Geocoding {}".format(addr)

    geo_result = self.client.geocode(addr)
    return (geo_result[0]['geometry']['location']['lat'], geo_result[0]['geometry']['location']['lng'])
