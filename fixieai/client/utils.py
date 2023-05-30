import contextlib
import functools
from typing import BinaryIO, Optional

from requests_toolbelt.multipart.encoder import MultipartEncoder  # type: ignore


@contextlib.contextmanager
def patched_gql_file_uploader(
    file_like: Optional[BinaryIO], name: str, content_type: str
):
    """Applies a temporary patch to allow setting name and Content-Type on uploads via `gql`.

    Future versions of `gql` will support setting Content-Type, but even with that support
    `gql` requires that the stream being uploaded is named and FixieClient does not. So this
    patches the underlying multipart encoder to assign the name and Content-Type to the specified
    stream.
    """

    if file_like is None:
        yield
        return

    @functools.wraps(MultipartEncoder.__init__)
    def _patched_init(self, fields, *args, **kwargs):
        patched_fields = {
            k: (
                (
                    name,
                    file_like,
                    content_type,
                )
                if len(v) == 2 and v[1] == file_like
                else v
            )
            for k, v in fields.items()
        }
        _patched_init.__wrapped__(self, patched_fields, *args, **kwargs)  # type: ignore

    try:
        MultipartEncoder.__init__ = _patched_init
        yield
    finally:
        MultipartEncoder.__init__ = _patched_init.__wrapped__  # type: ignore
