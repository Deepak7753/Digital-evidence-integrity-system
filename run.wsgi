import sys
import os

# Insert project directory to system paths
sys.path.insert(0, os.path.dirname(__file__))

# Activate virtual environment if needed
# activate_this = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'activate_this.py')
# if os.path.exists(activate_this):
#     exec(open(activate_this).read(), dict(__file__=activate_this))

from app import create_app

# WSGI Application entry point
application = create_app()
