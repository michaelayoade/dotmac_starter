def list_response(items: list, limit: int, offset: int) -> dict:
    return {"items": items, "count": len(items), "limit": limit, "offset": offset}


class ListResponseMixin:
    def list(self, db, *args, **kwargs):
        raise NotImplementedError

    def list_response(self, db, *args, **kwargs):
        if "limit" in kwargs and "offset" in kwargs:
            limit = kwargs["limit"]
            offset = kwargs["offset"]
            items = self.list(db, *args, **kwargs)
        else:
            if len(args) < 2:
                raise ValueError("limit and offset are required for list responses")
            *list_args, limit, offset = args
            items = self.list(db, *list_args, limit=limit, offset=offset, **kwargs)
        return list_response(items, limit, offset)
