# -*- coding: utf-8 -*-

import contextlib
import os
import stat
import sys
import tempfile


@contextlib.contextmanager
def open_for_atomic_write(filename, text=True, uid=None, gid=None, perm=None, tmp_suffix='.bak', tmp_prefix='tmp_', tmp_keep=True):
    '''Context manager for overwriting a file atomically.'''
    # Create temporary file
    path = os.path.dirname(filename)
    fd, filetmp = tempfile.mkstemp(dir=path, text=text, suffix=tmp_suffix, prefix=tmp_prefix)
    try:
        # Open remporary file for writing
        with os.fdopen(fd, 'w' if text else 'wb') as f:
            yield f
        # Rename to target
        os.replace(filetmp, filename) # atomic on POSIX systems and Windows for Python 3.3+
        filetmp = None
        # Set owner and permissions
        if any(x is None for x in (uid, gid, perm)):
            try:
                info = os.stat(filename)
                if uid is None:
                    uid = info.st_uid
                if gid is None:
                    gid = info.st_gid
                if perm is None:
                    perm = stat.S_IMODE(info.st_mode)
            except FileNotFoundError:
                pass
        if uid is None:
            uid = -1
        if gid is None:
            gid = -1
        os.chown(filename, uid, gid)
        if perm is not None:
            os.chmod(filename, perm)
    finally: # Silently try to delete the temporary file if needed
        if (filetmp is not None) and not tmp_keep: 
            try:
                os.unlink(filetmp)
            except:
                pass
