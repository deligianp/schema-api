def not_updatable(cls):
    save_method = cls.save

    def save(self, *args, **kwargs):
        if self.pk is not None:
            return
        save_method(self, *args, **kwargs)

    cls.save = save
    return cls
