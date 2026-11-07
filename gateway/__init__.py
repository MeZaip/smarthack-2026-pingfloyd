"""netcheck AI gateway: a small, locked-down HTTP service between the netcheck app and the model.

Only the team runs this, with the team's API key. End users never configure
anything: the app calls the gateway URL and falls back to built-in text if it
is unreachable.
"""
