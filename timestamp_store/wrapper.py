import ctypes
import platform
from pathlib import Path
from typing import List, Tuple, Optional, Union, Dict

class TimestampStore:
    _lib: ctypes.CDLL = None
    _lib_path: str = None

    @classmethod
    def _get_lib_name(cls) -> str:
        system = platform.system()
        if system == "Windows":
            return "timestamp_store.dll"
        elif system == "Darwin":
            return "libtimestamp_store.dylib"
        else:
            return "libtimestamp_store.so"

    @classmethod
    def _find_library(cls) -> str:
        lib_name = cls._get_lib_name()

        search_paths = [
            Path(__file__).parent / lib_name,
            Path(__file__).parent / "src" / lib_name,
            Path.cwd() / lib_name,
        ]

        for path in search_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError(
            f"Could not find {lib_name}. "
            f"Searched in: {[str(p) for p in search_paths]}. "
            f"Try reinstalling the package: pip install --force-reinstall git+https://github.com/shutkanos/timestamp_store.git"
        )

    @classmethod
    def _load_library(cls, lib_path: Optional[str] = None) -> ctypes.CDLL:
        if lib_path is None:
            lib_path = cls._find_library()

        if cls._lib is not None and cls._lib_path == lib_path:
            return cls._lib

        lib = ctypes.CDLL(lib_path)

        lib.ts_create.restype = ctypes.c_void_p
        lib.ts_create.argtypes = []

        lib.ts_create_from_arrays.restype = ctypes.c_void_p
        lib.ts_create_from_arrays.argtypes = [
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.c_int64
        ]

        lib.ts_destroy.restype = None
        lib.ts_destroy.argtypes = [ctypes.c_void_p]

        lib.ts_add.restype = None
        lib.ts_add.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64]

        lib.ts_remove.restype = ctypes.c_int32
        lib.ts_remove.argtypes = [ctypes.c_void_p, ctypes.c_int64]

        lib.ts_remove_before_timestamp.restype = ctypes.POINTER(ctypes.c_int64)
        lib.ts_remove_before_timestamp.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int64,
            ctypes.POINTER(ctypes.c_int64)
        ]

        lib.ts_free_array.restype = None
        lib.ts_free_array.argtypes = [ctypes.POINTER(ctypes.c_int64)]

        lib.ts_size.restype = ctypes.c_int64
        lib.ts_size.argtypes = [ctypes.c_void_p]

        lib.ts_empty.restype = ctypes.c_int32
        lib.ts_empty.argtypes = [ctypes.c_void_p]

        lib.ts_get_min_timestamp.restype = ctypes.c_int64
        lib.ts_get_min_timestamp.argtypes = [ctypes.c_void_p]

        lib.ts_contains.restype = ctypes.c_int32
        lib.ts_contains.argtypes = [ctypes.c_void_p, ctypes.c_int64]

        lib.ts_get_timestamp.restype = ctypes.c_int64
        lib.ts_get_timestamp.argtypes = [ctypes.c_void_p, ctypes.c_int64]

        cls._lib = lib
        cls._lib_path = lib_path
        return lib

    def __init__(self, data: Optional[Union[List[Tuple[int, int]], Dict[int, int]]] = None, *, lib_path: Optional[str] = None):
        self._lib_instance = self._load_library(lib_path)

        if data is None:
            self._store = self._lib_instance.ts_create()
        else:
            if isinstance(data, dict):
                pairs = list(data.items())
            else:
                pairs = list(data)

            if not pairs:
                self._store = self._lib_instance.ts_create()
            else:
                n = len(pairs)
                ids_array = (ctypes.c_int64 * n)()
                timestamps_array = (ctypes.c_int64 * n)()

                for i, (id_val, ts_val) in enumerate(pairs):
                    ids_array[i] = id_val
                    timestamps_array[i] = ts_val

                self._store = self._lib_instance.ts_create_from_arrays(
                    ids_array, timestamps_array, n
                )

        if not self._store:
            raise MemoryError("Failed to create TimestampStore")

    def __del__(self):
        if hasattr(self, '_store') and self._store and hasattr(self, '_lib_instance'):
            self._lib_instance.ts_destroy(self._store)
            self._store = None

    def add(self, id: int, timestamp: int) -> None:
        self._lib_instance.ts_add(self._store, id, timestamp)

    def remove(self, id: int) -> bool:
        return bool(self._lib_instance.ts_remove(self._store, id))

    def remove_timestamp(self, timestamp: int) -> List[int]:
        """
        Delete all elements with a timestamp value less than the specified argument
        :return: list of deleted IDs.
        """
        size = ctypes.c_int64(0)
        arr_ptr = self._lib_instance.ts_remove_before_timestamp(
            self._store,
            timestamp,
            ctypes.byref(size)
        )

        if size.value == 0 or not arr_ptr:
            return []

        try:
            result = [arr_ptr[i] for i in range(size.value)]
        finally:
            self._lib_instance.ts_free_array(arr_ptr)

        return result

    def get_timestamp(self, id: int) -> Optional[int]:
        ts = self._lib_instance.ts_get_timestamp(self._store, id)
        return ts if ts >= 0 else None

    def get_min_timestamp(self) -> Optional[int]:
        ts = self._lib_instance.ts_get_min_timestamp(self._store)
        return ts if ts >= 0 else None

    def __len__(self) -> int:
        return self._lib_instance.ts_size(self._store)

    def __bool__(self) -> bool:
        return not self._lib_instance.ts_empty(self._store)

    def __contains__(self, id: int) -> bool:
        return bool(self._lib_instance.ts_contains(self._store, id))