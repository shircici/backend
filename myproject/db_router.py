class ReadWriteRouter:
    """
    Simple read/write split router.
    - write: primary (default)
    - read: read_replica
    """

    route_app_labels = {"sku_mgt"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "read_replica"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "default"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Migrations always on primary.
        if app_label in self.route_app_labels:
            return db == "default"
        return None
