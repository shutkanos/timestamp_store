# TimestampStore

Fast data structure for (id, timestamp) pairs with O(log N) operations.
Warning! Created by claude-opus-4.5 without human intervention.

## Installation

```bash
pip install timestamp-store
```

**Requirements:** C++ compiler (g++, clang++, or MSVC)

### Installing compiler

- **Ubuntu/Debian:** `sudo apt install g++`
- **macOS:** `xcode-select --install`
- **Windows:** Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

## Usage

```python
from timestamp_store import TimestampStore

store = TimestampStore()

# Add pairs
store.add(1, 100)
store.add(2, 50)
store.add(3, 150)

# Remove all with timestamp < 120
removed = store.remove_timestamp(120)
print(removed)  # [2, 1]

# Remove by id
store.remove(3)

# Create from list
store = TimestampStore.from_list([(1, 100), (2, 200)])

# Create from dict
store = TimestampStore.from_dict({1: 100, 2: 200})
```

## Complexity

| Operation | Complexity |
|-----------|------------|
| `add(id, timestamp)` | O(log N) |
| `remove(id)` | O(log N) |
| `remove_timestamp(ts)` | O(K) where K = removed count |
