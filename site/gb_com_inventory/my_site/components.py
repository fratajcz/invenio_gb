from invenio_drafts_resources.services.records.components import ServiceComponent

class RestrictedByDefaultComponent(ServiceComponent):
    """Set record and file access to restricted on draft creation"""

    def create(self, identity, data=None, record=None, **kwargs):
        record.access.protection.files = "restricted"

    def update(self, identity, data=None, record=None, **kwargs):
        record.access.protection.files = "restricted"