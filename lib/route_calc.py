from geopy.distance import great_circle
from collections import OrderedDict
from operator import itemgetter

import smartystreets_python_sdk
import googlemaps

import os.path
import json

class Container(object):
  pass

class ContainerEncoder(json.JSONEncoder):
  def default(self, obj):
    return obj.__dict__

class RouteCalc:
  def __init__(self, config):
    self.cfg = config
    if self.cfg.google_api_key:
      self.google_client = googlemaps.Client(self.cfg.google_api_key)
    else:
      self.google_client = None
    if self.cfg.smarty_auth_id:
      credentials = smartystreets_python_sdk.StaticCredentials(self.cfg.smarty_auth_id, self.cfg.smarty_auth_token)
      self.smarty_client = smartystreets_python_sdk.ClientBuilder(credentials).build_us_street_api_client()
    else:
      self.smarty_client = None
    self.data = None

  def load_csv(self, csv_data):
    self.data = self.validate_data(csv_data)

  def load_json(self, filename):
    self.data = self.load_orders(filename)

  def route(self):
    if self.data == None:
      print("ERROR: load_csv or load_json not called first!")
      return -1

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
    return 0

  # private methods

  def validate_data(self, data):
    orders = {}
    loaded_orders = self.load_orders("{}/orders.json".format(self.cfg.output_dir))
    rowNum = 1
    for address in data:
      rowNum += 1
      if len(address[self.cfg.map_key('NAME')]) > 0 and len(address[self.cfg.map_key('ADDRESS')].strip()) > 0:
        entry = Container()
        entry.id = address[self.cfg.map_key('ID')]
        entry.name = address[self.cfg.map_key('NAME')]
        entry.address = "{}, {}, {} {}".format(address[self.cfg.map_key('ADDRESS')].strip(), 
                                               address[self.cfg.map_key('TOWN')].strip(), 
                                               address[self.cfg.map_key('STATE')].strip(), 
                                               address[self.cfg.map_key('ZIP')].strip().replace("'",""))
        entry.count = address[self.cfg.map_key('BAGS')]
        entry.comments = address[self.cfg.map_key('COMMENTS')]

        if entry.count == 0:
          print("ERROR: Order {} contains 0 items!".format(entry.id))
    
        # avoid expensive calculations by reusing the data from the loaded orders
        if entry.id in loaded_orders:
          entry.lat = loaded_orders[entry.id]['lat']
          entry.lon = loaded_orders[entry.id]['lon']
          entry.origin_dist = loaded_orders[entry.id]['origin_dist']
        else:
          (entry.lat, entry.lon) = self.geocode(address[self.cfg.map_key('ADDRESS')].strip(), 
                                                address[self.cfg.map_key('TOWN')].strip(), 
                                                address[self.cfg.map_key('STATE')].strip(), 
                                                address[self.cfg.map_key('ZIP')].strip().replace("'",""))
          entry.origin_dist = great_circle((self.cfg.origin[0], self.cfg.origin[1]), (entry.lat,entry.lon)).miles
    
        orders[entry.id] = entry
      else:
        print("ERROR: Bad entry in input '{}' in row {}".format(address[self.cfg.map_key('ID')], rowNum))

    self.save_orders(orders)

    return orders

  def chunk_deliveries(self, id, adjacencies, planned_deliveries):
    route = [id]

    # Start with the smallest truck capacity as we have more of those available
    count = self.cfg.truck_capacity("Box Truck") - int(self.data[id].count)

    if count < 0:
      print("ERROR: Order {} is {} items, which won't fit on a Box Truck!".format(id, self.data[id].count))
      # We upgrade to the next size of truck
      count = self.cfg.truck_capacity("18' Flatbed") - int(self.data[id].count)

    if count < 0:
      print("ERROR: Order {} is {} items, which won't fit on an 18' Flatbed!".format(id, self.data[id].count))
      # TODO: Try upgrading to the maximum size truck available -- For our troop we won't always get a 26' truck, 
      # so the next option would be to split the order (which is done manually by editing routes.json before printing)
 
    # FIXME: This simple algorithm is flawed in that homes which are close via geocoords can be far via roads.
    # An example is two homes which are back-to-back with a stream between their backyards (sometimes there's no
    # water feature and the neighborhoods have no access between them).
    for n in adjacencies[id]:
      # PRECOND: adjacencies is sorted nearest to fathest, thus if the distance is 3 or more away, break
      if n[1] > 3: break
      # Skip this adjacency if it's already in another delivery route
      if n[0] in planned_deliveries: continue
      # Skip this adjaceny if it's already in this delivery route
      if n[0] in route: continue
      # If there's enough space left on the truck for this delivery, add it and lower the remaining space
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
    if self.cfg.verbose:
      print("Calculating adjacencies")
    adjacencies = {}

    for k,v in self.data.items():
      if not k in adjacencies:
        adjacencies[k] = {}
      for l,w in self.data.items():
        if l == k: continue
        adjacencies[k][l] = great_circle((v.lat, v.lon), (w.lat, w.lon)).miles

    # Now that we've calculated all of the adjacencies, let's order them by distance
    for a in adjacencies:
      adjacencies[a] = sorted(adjacencies[a].items(), key=itemgetter(1))

    self.save_adjacencies(adjacencies)

    return adjacencies

  def load_adjacencies(self):
    adjacencies = {}
    savefile = "{}/adjacencies.json".format(self.cfg.output_dir)

    if os.path.isfile(savefile): 
      with open(savefile, 'r') as json_data:
        adjacencies = json.load(json_data)

    if self.cfg.verbose:
      print("Loaded {} adjacencies from {}".format(len(adjacencies), savefile))

    return adjacencies

  def save_adjacencies(self, data):
    savefile = "{}/adjacencies.json".format(self.cfg.output_dir)

    with open(savefile, 'w') as f:
      json.dump(data, f, indent=2, cls=ContainerEncoder)

    if self.cfg.verbose:
      print("Saved {} adjacencies to {}".format(len(data), savefile))

  def load_orders(self, savefile):
    orders = {}

    if os.path.isfile(savefile): 
      with open(savefile, 'r') as json_data:
        orders = json.load(json_data)

    if self.cfg.verbose:
      print("Loaded {} orders from {}".format(len(orders), savefile))

    return orders

  def save_orders(self, data):
    savefile = "{}/orders.json".format(self.cfg.output_dir)

    if not os.path.exists(self.cfg.output_dir):
      os.makedirs(self.cfg.output_dir)

    with open(savefile, 'w') as f:
      json.dump(data, f, indent=2, cls=ContainerEncoder)

    if self.cfg.verbose:
      print("Saved {} orders to {}".format(len(data), savefile))

  def save_routes(self, routes):
    savefile = "{}/routes.json".format(self.cfg.output_dir)

    with open(savefile, 'w') as f:
      json.dump(routes, f, indent=2, cls=ContainerEncoder)

    if self.cfg.verbose:
      print("Saved {} routes with {} orders to {}".format(len(routes), self.count_orders_in_routes(routes), savefile))

  def count_orders_in_routes(self, routes):
    orders = 0
    for r in routes:
      orders += len(r)

    return orders

  def geocode(self, street, city, state, zipc):
    addr = "{} {}, {} {}".format(street, city, state, zipc)

    if self.smarty_client:
      if self.cfg.verbose:
        print("Geocoding '{}' with SmartyStreets".format(addr))
      
      lookup = smartystreets_python_sdk.us_street.Lookup()
      lookup.street = street
      lookup.city = city
      lookup.state = state
      #lookup.zip = zipc
      try:
        self.smarty_client.send_lookup(lookup)
      except smartystreets_python_sdk.exceptions.SmartyException as err:
        print(err)
        return (0,0)

      if not lookup.result:
        print("ERROR: Cannot geocode {}: invalid!".format(addr))
        return (None,None)

      return (lookup.result[0].metadata.latitude, lookup.result[0].metadata.longitude)
    elif self.google_client:
      if self.cfg.verbose:
        print("Geocoding '{}' with Google".format(addr))

      geo_result = self.google_client.geocode(addr)
      if len(geo_result) < 1:
        print("ERROR: Unable to geocode '{}' with Google".format(addr))
      else:
        return (geo_result[0]['geometry']['location']['lat'], geo_result[0]['geometry']['location']['lng'])
    return (0,0)
