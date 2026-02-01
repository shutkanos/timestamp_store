#include <map>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <cstdint>
#include <algorithm>

class TimestampStore {
private:
    std::map<int64_t, std::unordered_set<int64_t>> time_to_ids_;

    std::unordered_map<int64_t, int64_t> id_to_time_;

public:
    TimestampStore() = default;

    void add(int64_t id, int64_t timestamp) {
        auto it = id_to_time_.find(id);

        if (it != id_to_time_.end()) {
            int64_t old_time = it->second;

            if (old_time == timestamp) {
                return;
            }

            auto old_time_it = time_to_ids_.find(old_time);
            if (old_time_it != time_to_ids_.end()) {
                old_time_it->second.erase(id);
                if (old_time_it->second.empty()) {
                    time_to_ids_.erase(old_time_it);
                }
            }

            it->second = timestamp;
        } else {
            id_to_time_[id] = timestamp;
        }

        time_to_ids_[timestamp].insert(id);
    }

    bool remove(int64_t id) {
        auto it = id_to_time_.find(id);
        if (it == id_to_time_.end()) {
            return false;
        }

        int64_t timestamp = it->second;
        id_to_time_.erase(it);

        auto time_it = time_to_ids_.find(timestamp);
        if (time_it != time_to_ids_.end()) {
            time_it->second.erase(id);
            if (time_it->second.empty()) {
                time_to_ids_.erase(time_it);
            }
        }

        return true;
    }

    std::vector<int64_t> remove_before_timestamp(int64_t timestamp) {
        std::vector<int64_t> removed_ids;

        while (!time_to_ids_.empty()) {
            auto it = time_to_ids_.begin();

            if (it->first >= timestamp) {
                break;
            }

            for (int64_t id : it->second) {
                removed_ids.push_back(id);
                id_to_time_.erase(id);
            }

            time_to_ids_.erase(it);
        }

        return removed_ids;
    }

    size_t size() const {
        return id_to_time_.size();
    }

    bool empty() const {
        return id_to_time_.empty();
    }

    int64_t get_min_timestamp() const {
        if (time_to_ids_.empty()) {
            return -1;
        }
        return time_to_ids_.begin()->first;
    }

    bool contains(int64_t id) const {
        return id_to_time_.count(id) > 0;
    }

    int64_t get_timestamp(int64_t id) const {
        auto it = id_to_time_.find(id);
        if (it == id_to_time_.end()) {
            return -1;
        }
        return it->second;
    }
};


// ============================================================================
// C API ctypes
// ============================================================================

#ifdef _WIN32
    #define EXPORT extern "C" __declspec(dllexport)
#else
    #define EXPORT extern "C" __attribute__((visibility("default")))
#endif

EXPORT TimestampStore* ts_create() {
    return new TimestampStore();
}

EXPORT TimestampStore* ts_create_from_arrays(
    const int64_t* ids,
    const int64_t* timestamps,
    int64_t count
) {
    TimestampStore* store = new TimestampStore();
    for (int64_t i = 0; i < count; ++i) {
        store->add(ids[i], timestamps[i]);
    }
    return store;
}

EXPORT void ts_destroy(TimestampStore* store) {
    delete store;
}

EXPORT void ts_add(TimestampStore* store, int64_t id, int64_t timestamp) {
    if (store) {
        store->add(id, timestamp);
    }
}

EXPORT int32_t ts_remove(TimestampStore* store, int64_t id) {
    if (!store) return 0;
    return store->remove(id) ? 1 : 0;
}

EXPORT int64_t* ts_remove_before_timestamp(
    TimestampStore* store,
    int64_t timestamp,
    int64_t* out_size
) {
    if (!store || !out_size) {
        if (out_size) *out_size = 0;
        return nullptr;
    }

    std::vector<int64_t> result = store->remove_before_timestamp(timestamp);
    *out_size = static_cast<int64_t>(result.size());

    if (result.empty()) {
        return nullptr;
    }

    int64_t* arr = new int64_t[result.size()];
    std::copy(result.begin(), result.end(), arr);
    return arr;
}

EXPORT void ts_free_array(int64_t* arr) {
    delete[] arr;
}

EXPORT int64_t ts_size(TimestampStore* store) {
    if (!store) return 0;
    return static_cast<int64_t>(store->size());
}

EXPORT int32_t ts_empty(TimestampStore* store) {
    if (!store) return 1;
    return store->empty() ? 1 : 0;
}

EXPORT int64_t ts_get_min_timestamp(TimestampStore* store) {
    if (!store) return -1;
    return store->get_min_timestamp();
}

EXPORT int32_t ts_contains(TimestampStore* store, int64_t id) {
    if (!store) return 0;
    return store->contains(id) ? 1 : 0;
}

EXPORT int64_t ts_get_timestamp(TimestampStore* store, int64_t id) {
    if (!store) return -1;
    return store->get_timestamp(id);
}