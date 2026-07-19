from . import auth, dashboard, forms, training, stats, annual_ai, admin, cleo_api, reports, reconstruction, officers, ops_modules, legal, orders, reference, announcements, mobile
from . import credit_simulator

# Nest the private simulator under a blueprint already registered by the app
# factory, avoiding any change to the large central application factory.
admin.bp.register_blueprint(credit_simulator.bp)
