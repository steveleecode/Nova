import ctypes
from ctypes import wintypes
import win32file
import win32con
import os
import win32api

# Windows API constants for USN Journal
FSCTL_QUERY_USN_JOURNAL = 0x9004F
FSCTL_ENUM_USN_DATA = 0x900B3

class USN_RECORD(ctypes.Structure):
    _fields_ = [
        ("RecordLength", wintypes.DWORD),
        ("MajorVersion", wintypes.WORD),
        ("MinorVersion", wintypes.WORD),
        ("FileReferenceNumber", wintypes.ULARGE_INTEGER),
        ("ParentFileReferenceNumber", wintypes.ULARGE_INTEGER),
        ("USN", wintypes.LARGE_INTEGER),
        ("TimeStamp", wintypes.LARGE_INTEGER),
        ("Reason", wintypes.DWORD),
        ("SourceInfo", wintypes.DWORD),
        ("SecurityId", wintypes.DWORD),
        ("FileAttributes", wintypes.DWORD),
        ("FileNameLength", wintypes.WORD),
        ("FileNameOffset", wintypes.WORD),
        ("FileName", wintypes.WCHAR * 1)
    ]

def is_ntfs_drive(path: str) -> bool:
    """Check if the given path is on an NTFS drive."""
    try:
        drive = os.path.splitdrive(path)[0]
        fs_type = win32api.GetVolumeInformation(drive + "\\")[4]
        return fs_type == "NTFS"
    except:
        return False 