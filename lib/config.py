import os

class Config:
  def __init__(self):
    self.smarty_auth_id = None
    self.smarty_auth_token = None
    self.google_api_key = None
    self.trucks = [{ "type": "Box Truck", "capacity": 135 }, {"type": "26' Flatbed", "capacity": 315 }]
    self.contact = "(123) 456-7890 (John Smith)"
    self.output_dir = "output"
    self.processes = 8
    self.origin = [38.950633, -77.397684]
    self.mappings = {}
    self.verbose = None

    self._load_env_vars()
    self._setup_mappings()

  def map_key(self, key):
    if key in self.mappings:
      return self.mappings[key]
    return key

  def _load_env_vars(self):
    try:
      self.smarty_auth_id = os.environ['SMARTY_AUTH_ID']
    except KeyError:
      pass
    try:
      self.smarty_auth_token = os.environ['SMARTY_AUTH_TOKEN']
    except KeyError:
      pass
    try:
      self.google_api_key = os.environ['GOOGLE_API_KEY']
    except KeyError:
      pass
    try:
      self.contact = os.environ["CONTACT"]
    except KeyError:
      pass

  def _setup_mappings(self):
    self.mappings = { 
      'BD ID': 'Name',
      'NAME': 'Shipping Name',
      'ADDRESS': 'Shipping Street',
      'TOWN': 'Shipping City',
      'STATE': 'Shipping Province',
      'ZIP': 'Shipping Zip',
      'BAGS': 'Lineitem quantity',
      'COMMENTS': 'Notes'
    }