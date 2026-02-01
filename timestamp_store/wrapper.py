"""
Python wrapper для TimestampStore через ctypes
"""

import ctypes
import os
import platform
from pathlib import Path
from typing import List, Tuple, Optional


class TimestampStore:
    """
    Структура данных для хранения пар (id, timestamp)

    Сложности:
    - add(id, timestamp): O(log N)
    - remove(id): O(log N)
    - remove_timestamp(ts): O(K), где K - кол-во удалённых (O(1) на элемент)
    """

    _lib: ctypes.CDLL = None
    _lib_path: str = None

    @classmethod
    def _get_lib_name(cls) -> str:
        """Получить имя библиотеки для текущей платформы"""
        system = platform.system()
        if system == "Windows":
            return "timestamp_store.dll"
        elif system == "Darwin":
            return "libtimestamp_store.dylib"
        else:
            return "libtimestamp_store.so"

    @classmethod
    def _find_library(cls) -> str:
        """Найти скомпилированную библиотеку"""
        lib_name = cls._get_lib_name()

        # Варианты расположения библиотеки
        search_paths = [
            # Рядом с этим файлом (после установки)
            Path(__file__).parent / lib_name,
            # В директории src (для разработки)
            Path(__file__).parent / "src" / lib_name,
            # В текущей директории
            Path.cwd() / lib_name,
        ]

        for path in search_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError(
            f"Could not find {lib_name}. "
            f"Searched in: {[str(p) for p in search_paths]}. "
            f"Try reinstalling the package: pip install --force-reinstall timestamp-store"
        )

    @classmethod
    def _load_library(cls, lib_path: Optional[str] = None) -> ctypes.CDLL:
        """Загрузить библиотеку (с кешированием)"""
        if lib_path is None:
            lib_path = cls._find_library()

        if cls._lib is not None and cls._lib_path == lib_path:
            return cls._lib

        lib = ctypes.CDLL(lib_path)

        # Определяем сигнатуры функций

        # TimestampStore* ts_create()
        lib.ts_create.restype = ctypes.c_void_p
        lib.ts_create.argtypes = []

        # TimestampStore* ts_create_from_arrays(int64_t*, int64_t*, int64_t)
        lib.ts_create_from_arrays.restype = ctypes.c_void_p
        lib.ts_create_from_arrays.argtypes = [
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.c_int64
        ]

        # void ts_destroy(TimestampStore*)
        lib.ts_destroy.restype = None
        lib.ts_destroy.argtypes = [ctypes.c_void_p]

        # void ts_add(TimestampStore*, int64_t, int64_t)
        lib.ts_add.restype = None
        lib.ts_add.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64]

        # int32_t ts_remove(TimestampStore*, int64_t)
        lib.ts_remove.restype = ctypes.c_int32
        lib.ts_remove.argtypes = [ctypes.c_void_p, ctypes.c_int64]

        # int64_t* ts_remove_before_timestamp(TimestampStore*, int64_t, int64_t*)
        lib.ts_remove_before_timestamp.restype = ctypes.POINTER(ctypes.c_int64)
        lib.ts_remove_before_timestamp.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int64,
            ctypes.POINTER(ctypes.c_int64)
        ]

        # void ts_free_array(int64_t*)
        lib.ts_free_array.restype = None
        lib.ts_free_array.argtypes = [ctypes.POINTER(ctypes.c_int64)]

        # int64_t ts_size(TimestampStore*)
        lib.ts_size.restype = ctypes.c_int64
        lib.ts_size.argtypes = [ctypes.c_void_p]

        # int32_t ts_empty(TimestampStore*)
        lib.ts_empty.restype = ctypes.c_int32
        lib.ts_empty.argtypes = [ctypes.c_void_p]

        # int64_t ts_get_min_timestamp(TimestampStore*)
        lib.ts_get_min_timestamp.restype = ctypes.c_int64
        lib.ts_get_min_timestamp.argtypes = [ctypes.c_void_p]

        # int32_t ts_contains(TimestampStore*, int64_t)
        lib.ts_contains.restype = ctypes.c_int32
        lib.ts_contains.argtypes = [ctypes.c_void_p, ctypes.c_int64]

        # int64_t ts_get_timestamp(TimestampStore*, int64_t)
        lib.ts_get_timestamp.restype = ctypes.c_int64
        lib.ts_get_timestamp.argtypes = [ctypes.c_void_p, ctypes.c_int64]

        cls._lib = lib
        cls._lib_path = lib_path
        return lib

    def __init__(self, lib_path: Optional[str] = None):
        """Создать пустое хранилище"""
        self._lib = self._load_library(lib_path)
        self._store = self._lib.ts_create()
        if not self._store:
            raise MemoryError("Failed to create TimestampStore")

    def __del__(self):
        """Освободить ресурсы"""
        if hasattr(self, '_store') and self._store and hasattr(self, '_lib'):
            self._lib.ts_destroy(self._store)
            self._store = None

    def __len__(self) -> int:
        return self._lib.ts_size(self._store)

    def __bool__(self) -> bool:
        return not self._lib.ts_empty(self._store)

    def __contains__(self, id: int) -> bool:
        return bool(self._lib.ts_contains(self._store, id))

    def add(self, id: int, timestamp: int) -> None:
        """Добавить пару (id, timestamp). O(log N)"""
        self._lib.ts_add(self._store, id, timestamp)

    def remove(self, id: int) -> bool:
        """Удалить по id. O(log N). Возвращает True если элемент был найден."""
        return bool(self._lib.ts_remove(self._store, id))

    def remove_timestamp(self, timestamp: int) -> List[int]:
        """Удалить все элементы с timestamp < заданного. O(1) на элемент."""
        size = ctypes.c_int64(0)
        arr_ptr = self._lib.ts_remove_before_timestamp(
            self._store,
            timestamp,
            ctypes.byref(size)
        )

        if size.value == 0 or not arr_ptr:
            return []

        try:
            result = [arr_ptr[i] for i in range(size.value)]
        finally:
            self._lib.ts_free_array(arr_ptr)

        return result

    def get_timestamp(self, id: int) -> Optional[int]:
        """Получить timestamp по id. O(1)."""
        ts = self._lib.ts_get_timestamp(self._store, id)
        return ts if ts >= 0 else None

    def get_min_timestamp(self) -> Optional[int]:
        """Получить минимальный timestamp. O(1)."""
        ts = self._lib.ts_get_min_timestamp(self._store)
        return ts if ts >= 0 else None

    @classmethod
    def from_list(
            cls,
            pairs: List[Tuple[int, int]],
            lib_path: Optional[str] = None
    ) -> 'TimestampStore':
        """Создать из списка пар [(id, timestamp), ...]"""
        if not pairs:
            return cls(lib_path)

        lib = cls._load_library(lib_path)

        n = len(pairs)
        ids_array = (ctypes.c_int64 * n)()
        timestamps_array = (ctypes.c_int64 * n)()

        for i, (id_val, ts_val) in enumerate(pairs):
            ids_array[i] = id_val
            timestamps_array[i] = ts_val

        store_ptr = lib.ts_create_from_arrays(ids_array, timestamps_array, n)

        if not store_ptr:
            raise MemoryError("Failed to create TimestampStore from arrays")

        instance = object.__new__(cls)
        instance._lib = lib
        instance._store = store_ptr
        return instance

    @classmethod
    def from_dict(
            cls,
            data: dict,
            lib_path: Optional[str] = None
    ) -> 'TimestampStore':
        """Создать из словаря {id: timestamp}"""
        return cls.from_list(list(data.items()), lib_path)