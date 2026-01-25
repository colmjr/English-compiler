/**
 * Core IL Runtime Library for C++
 *
 * This header provides the runtime support for Core IL v1.5 programs compiled to C++.
 * It implements Python-compatible semantics for all operations.
 *
 * Requirements: C++17 (for std::variant, std::optional)
 * Optional: nlohmann/json.hpp for JSON operations (include before this header)
 *
 * Version: 1.5
 */

#ifndef COREIL_RUNTIME_HPP
#define COREIL_RUNTIME_HPP

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <deque>
#include <functional>
#include <iostream>
#include <memory>
#include <optional>
#include <queue>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <variant>
#include <vector>

namespace coreil {

// Forward declarations
struct Array;
struct Tuple;
struct Map;
struct Set;
struct Record;
struct Deque;
struct Heap;

/**
 * The universal Value type for Core IL.
 * Uses shared_ptr for reference semantics on complex types.
 */
using Value = std::variant<
    std::nullptr_t,                      // None
    bool,                                // Boolean
    int64_t,                             // Integer
    double,                              // Float
    std::string,                         // String
    std::shared_ptr<Tuple>,              // Immutable tuple
    std::shared_ptr<Array>,              // Mutable array
    std::shared_ptr<Map>,                // Ordered map (insertion order)
    std::shared_ptr<Set>,                // Set (ordered by insertion for determinism)
    std::shared_ptr<Record>,             // Mutable named fields
    std::shared_ptr<Deque>,              // Double-ended queue
    std::shared_ptr<Heap>                // Min-heap priority queue
>;

// ============================================================================
// Data Structure Definitions
// ============================================================================

struct Array {
    std::vector<Value> items;
    Array() = default;
    explicit Array(std::vector<Value> items) : items(std::move(items)) {}
};

struct Tuple {
    std::vector<Value> items;
    Tuple() = default;
    explicit Tuple(std::vector<Value> items) : items(std::move(items)) {}
};

/**
 * Map preserves insertion order (like Python 3.7+ dict).
 * We use a vector for ordered storage and a hash map for O(1) lookup.
 */
struct Map {
    std::vector<std::pair<Value, Value>> items;
    std::unordered_map<std::string, size_t> index;  // serialized key -> position

    Map() = default;
};

struct Set {
    std::vector<Value> items;  // Ordered by insertion
    std::unordered_set<std::string> index;  // serialized items for O(1) lookup

    Set() = default;
};

struct Record {
    std::unordered_map<std::string, Value> fields;

    Record() = default;
};

struct Deque {
    std::deque<Value> items;

    Deque() = default;
};

/**
 * Min-heap with stable ordering (tie-breaker by insertion order).
 */
struct Heap {
    struct Entry {
        double priority;
        int64_t counter;
        Value value;

        bool operator>(const Entry& other) const {
            if (priority != other.priority) return priority > other.priority;
            return counter > other.counter;
        }
    };

    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> pq;
    int64_t counter = 0;

    Heap() = default;
};

// ============================================================================
// Value Serialization (for map/set keys)
// ============================================================================

// Forward declaration
std::string serialize_value(const Value& v);

inline std::string serialize_value(const Value& v) {
    return std::visit([](auto&& arg) -> std::string {
        using T = std::decay_t<decltype(arg)>;
        if constexpr (std::is_same_v<T, std::nullptr_t>) {
            return "N";
        } else if constexpr (std::is_same_v<T, bool>) {
            return arg ? "B1" : "B0";
        } else if constexpr (std::is_same_v<T, int64_t>) {
            return "I" + std::to_string(arg);
        } else if constexpr (std::is_same_v<T, double>) {
            std::ostringstream oss;
            oss.precision(17);
            oss << "D" << arg;
            return oss.str();
        } else if constexpr (std::is_same_v<T, std::string>) {
            return "S" + std::to_string(arg.size()) + ":" + arg;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Tuple>>) {
            std::string result = "T[";
            for (size_t i = 0; i < arg->items.size(); ++i) {
                if (i > 0) result += ",";
                result += serialize_value(arg->items[i]);
            }
            result += "]";
            return result;
        } else {
            throw std::runtime_error("unhashable type used as key");
        }
    }, v);
}

// ============================================================================
// Value Formatting (Python-compatible output)
// ============================================================================

// Forward declaration
std::string format(const Value& v);

inline std::string format(const Value& v) {
    return std::visit([](auto&& arg) -> std::string {
        using T = std::decay_t<decltype(arg)>;
        if constexpr (std::is_same_v<T, std::nullptr_t>) {
            return "None";
        } else if constexpr (std::is_same_v<T, bool>) {
            return arg ? "True" : "False";
        } else if constexpr (std::is_same_v<T, int64_t>) {
            return std::to_string(arg);
        } else if constexpr (std::is_same_v<T, double>) {
            std::ostringstream oss;
            // Check if it's an integer value
            if (std::floor(arg) == arg && std::abs(arg) < 1e15) {
                oss << static_cast<int64_t>(arg) << ".0";
            } else {
                oss.precision(15);
                oss << arg;
            }
            return oss.str();
        } else if constexpr (std::is_same_v<T, std::string>) {
            return arg;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Tuple>>) {
            std::string result = "(";
            for (size_t i = 0; i < arg->items.size(); ++i) {
                if (i > 0) result += ", ";
                // For tuples, strings should be quoted
                const Value& item = arg->items[i];
                if (std::holds_alternative<std::string>(item)) {
                    result += "'" + std::get<std::string>(item) + "'";
                } else {
                    result += format(item);
                }
            }
            if (arg->items.size() == 1) result += ",";
            result += ")";
            return result;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Array>>) {
            std::string result = "[";
            for (size_t i = 0; i < arg->items.size(); ++i) {
                if (i > 0) result += ", ";
                const Value& item = arg->items[i];
                if (std::holds_alternative<std::string>(item)) {
                    result += "'" + std::get<std::string>(item) + "'";
                } else {
                    result += format(item);
                }
            }
            result += "]";
            return result;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Map>>) {
            std::string result = "{";
            bool first = true;
            for (const auto& [k, v] : arg->items) {
                if (!first) result += ", ";
                first = false;
                // Format key
                if (std::holds_alternative<std::string>(k)) {
                    result += "'" + std::get<std::string>(k) + "'";
                } else {
                    result += format(k);
                }
                result += ": ";
                // Format value
                if (std::holds_alternative<std::string>(v)) {
                    result += "'" + std::get<std::string>(v) + "'";
                } else {
                    result += format(v);
                }
            }
            result += "}";
            return result;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Set>>) {
            if (arg->items.empty()) return "set()";
            std::string result = "{";
            for (size_t i = 0; i < arg->items.size(); ++i) {
                if (i > 0) result += ", ";
                const Value& item = arg->items[i];
                if (std::holds_alternative<std::string>(item)) {
                    result += "'" + std::get<std::string>(item) + "'";
                } else {
                    result += format(item);
                }
            }
            result += "}";
            return result;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Record>>) {
            std::string result = "{";
            bool first = true;
            for (const auto& [k, v] : arg->fields) {
                if (!first) result += ", ";
                first = false;
                result += "'" + k + "': ";
                if (std::holds_alternative<std::string>(v)) {
                    result += "'" + std::get<std::string>(v) + "'";
                } else {
                    result += format(v);
                }
            }
            result += "}";
            return result;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Deque>>) {
            std::string result = "deque([";
            bool first = true;
            for (const auto& item : arg->items) {
                if (!first) result += ", ";
                first = false;
                if (std::holds_alternative<std::string>(item)) {
                    result += "'" + std::get<std::string>(item) + "'";
                } else {
                    result += format(item);
                }
            }
            result += "])";
            return result;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Heap>>) {
            return "<heap>";
        } else {
            return "<unknown>";
        }
    }, v);
}

// ============================================================================
// Print Function
// ============================================================================

inline void print(std::initializer_list<Value> args) {
    bool first = true;
    for (const auto& arg : args) {
        if (!first) std::cout << " ";
        first = false;
        std::cout << format(arg);
    }
    std::cout << "\n";
}

inline void print(const std::vector<Value>& args) {
    bool first = true;
    for (const auto& arg : args) {
        if (!first) std::cout << " ";
        first = false;
        std::cout << format(arg);
    }
    std::cout << "\n";
}

// ============================================================================
// Type Checking and Coercion
// ============================================================================

inline bool is_truthy(const Value& v) {
    return std::visit([](auto&& arg) -> bool {
        using T = std::decay_t<decltype(arg)>;
        if constexpr (std::is_same_v<T, std::nullptr_t>) {
            return false;
        } else if constexpr (std::is_same_v<T, bool>) {
            return arg;
        } else if constexpr (std::is_same_v<T, int64_t>) {
            return arg != 0;
        } else if constexpr (std::is_same_v<T, double>) {
            return arg != 0.0;
        } else if constexpr (std::is_same_v<T, std::string>) {
            return !arg.empty();
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Array>>) {
            return !arg->items.empty();
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Tuple>>) {
            return !arg->items.empty();
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Map>>) {
            return !arg->items.empty();
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Set>>) {
            return !arg->items.empty();
        } else {
            return true;
        }
    }, v);
}

inline int64_t as_int(const Value& v) {
    if (auto* i = std::get_if<int64_t>(&v)) return *i;
    if (auto* d = std::get_if<double>(&v)) return static_cast<int64_t>(*d);
    if (auto* b = std::get_if<bool>(&v)) return *b ? 1 : 0;
    throw std::runtime_error("cannot convert to integer");
}

inline double as_number(const Value& v) {
    if (auto* i = std::get_if<int64_t>(&v)) return static_cast<double>(*i);
    if (auto* d = std::get_if<double>(&v)) return *d;
    if (auto* b = std::get_if<bool>(&v)) return *b ? 1.0 : 0.0;
    throw std::runtime_error("cannot convert to number");
}

inline std::string as_string(const Value& v) {
    if (auto* s = std::get_if<std::string>(&v)) return *s;
    return format(v);
}

inline std::shared_ptr<Array> as_array(const Value& v) {
    if (auto* a = std::get_if<std::shared_ptr<Array>>(&v)) return *a;
    throw std::runtime_error("expected array");
}

inline std::shared_ptr<Tuple> as_tuple(const Value& v) {
    if (auto* t = std::get_if<std::shared_ptr<Tuple>>(&v)) return *t;
    throw std::runtime_error("expected tuple");
}

inline std::shared_ptr<Map> as_map(const Value& v) {
    if (auto* m = std::get_if<std::shared_ptr<Map>>(&v)) return *m;
    throw std::runtime_error("expected map");
}

inline std::shared_ptr<Set> as_set(const Value& v) {
    if (auto* s = std::get_if<std::shared_ptr<Set>>(&v)) return *s;
    throw std::runtime_error("expected set");
}

inline std::shared_ptr<Record> as_record(const Value& v) {
    if (auto* r = std::get_if<std::shared_ptr<Record>>(&v)) return *r;
    throw std::runtime_error("expected record");
}

inline std::shared_ptr<Deque> as_deque(const Value& v) {
    if (auto* d = std::get_if<std::shared_ptr<Deque>>(&v)) return *d;
    throw std::runtime_error("expected deque");
}

inline std::shared_ptr<Heap> as_heap(const Value& v) {
    if (auto* h = std::get_if<std::shared_ptr<Heap>>(&v)) return *h;
    throw std::runtime_error("expected heap");
}

// ============================================================================
// Binary Operations
// ============================================================================

inline Value add(const Value& left, const Value& right) {
    // String concatenation
    if (std::holds_alternative<std::string>(left) || std::holds_alternative<std::string>(right)) {
        return as_string(left) + as_string(right);
    }
    // Array concatenation
    if (auto* la = std::get_if<std::shared_ptr<Array>>(&left)) {
        if (auto* ra = std::get_if<std::shared_ptr<Array>>(&right)) {
            auto result = std::make_shared<Array>();
            result->items = (*la)->items;
            result->items.insert(result->items.end(), (*ra)->items.begin(), (*ra)->items.end());
            return result;
        }
    }
    // Numeric addition
    bool left_float = std::holds_alternative<double>(left);
    bool right_float = std::holds_alternative<double>(right);
    if (left_float || right_float) {
        return as_number(left) + as_number(right);
    }
    return as_int(left) + as_int(right);
}

inline Value subtract(const Value& left, const Value& right) {
    bool left_float = std::holds_alternative<double>(left);
    bool right_float = std::holds_alternative<double>(right);
    if (left_float || right_float) {
        return as_number(left) - as_number(right);
    }
    return as_int(left) - as_int(right);
}

inline Value multiply(const Value& left, const Value& right) {
    // String * int repetition
    if (auto* s = std::get_if<std::string>(&left)) {
        int64_t n = as_int(right);
        std::string result;
        for (int64_t i = 0; i < n; ++i) result += *s;
        return result;
    }
    if (auto* s = std::get_if<std::string>(&right)) {
        int64_t n = as_int(left);
        std::string result;
        for (int64_t i = 0; i < n; ++i) result += *s;
        return result;
    }
    // Numeric multiplication
    bool left_float = std::holds_alternative<double>(left);
    bool right_float = std::holds_alternative<double>(right);
    if (left_float || right_float) {
        return as_number(left) * as_number(right);
    }
    return as_int(left) * as_int(right);
}

inline Value divide(const Value& left, const Value& right) {
    // Division always returns float in Python 3
    double l = as_number(left);
    double r = as_number(right);
    if (r == 0) throw std::runtime_error("division by zero");
    return l / r;
}

inline Value modulo(const Value& left, const Value& right) {
    // Python-style modulo (result has same sign as divisor)
    bool left_float = std::holds_alternative<double>(left);
    bool right_float = std::holds_alternative<double>(right);

    if (left_float || right_float) {
        double l = as_number(left);
        double r = as_number(right);
        if (r == 0) throw std::runtime_error("modulo by zero");
        double result = std::fmod(l, r);
        // Python semantics: result has same sign as divisor
        if ((result < 0) != (r < 0) && result != 0) {
            result += r;
        }
        return result;
    }

    int64_t l = as_int(left);
    int64_t r = as_int(right);
    if (r == 0) throw std::runtime_error("modulo by zero");
    int64_t result = l % r;
    // Python semantics: result has same sign as divisor
    if ((result < 0) != (r < 0) && result != 0) {
        result += r;
    }
    return result;
}

// Deep equality comparison
inline bool equal(const Value& left, const Value& right);

inline bool equal(const Value& left, const Value& right) {
    // Type mismatch - check for numeric comparison
    if (left.index() != right.index()) {
        // Allow int/float comparison
        bool left_numeric = std::holds_alternative<int64_t>(left) || std::holds_alternative<double>(left);
        bool right_numeric = std::holds_alternative<int64_t>(right) || std::holds_alternative<double>(right);
        if (left_numeric && right_numeric) {
            return as_number(left) == as_number(right);
        }
        // bool can compare with numeric
        if (std::holds_alternative<bool>(left) && right_numeric) {
            return (std::get<bool>(left) ? 1.0 : 0.0) == as_number(right);
        }
        if (std::holds_alternative<bool>(right) && left_numeric) {
            return as_number(left) == (std::get<bool>(right) ? 1.0 : 0.0);
        }
        return false;
    }

    return std::visit([&right](auto&& arg) -> bool {
        using T = std::decay_t<decltype(arg)>;
        if constexpr (std::is_same_v<T, std::nullptr_t>) {
            return true;
        } else if constexpr (std::is_same_v<T, bool> || std::is_same_v<T, int64_t> ||
                           std::is_same_v<T, double> || std::is_same_v<T, std::string>) {
            return arg == std::get<T>(right);
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Tuple>>) {
            auto& r = std::get<std::shared_ptr<Tuple>>(right);
            if (arg->items.size() != r->items.size()) return false;
            for (size_t i = 0; i < arg->items.size(); ++i) {
                if (!equal(arg->items[i], r->items[i])) return false;
            }
            return true;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Array>>) {
            auto& r = std::get<std::shared_ptr<Array>>(right);
            if (arg->items.size() != r->items.size()) return false;
            for (size_t i = 0; i < arg->items.size(); ++i) {
                if (!equal(arg->items[i], r->items[i])) return false;
            }
            return true;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Map>>) {
            auto& r = std::get<std::shared_ptr<Map>>(right);
            if (arg->items.size() != r->items.size()) return false;
            for (size_t i = 0; i < arg->items.size(); ++i) {
                if (!equal(arg->items[i].first, r->items[i].first)) return false;
                if (!equal(arg->items[i].second, r->items[i].second)) return false;
            }
            return true;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Set>>) {
            auto& r = std::get<std::shared_ptr<Set>>(right);
            return arg->index == r->index;
        } else {
            // Reference equality for other types
            return false;
        }
    }, left);
}

inline bool less_than(const Value& left, const Value& right) {
    // Numeric comparison
    if ((std::holds_alternative<int64_t>(left) || std::holds_alternative<double>(left)) &&
        (std::holds_alternative<int64_t>(right) || std::holds_alternative<double>(right))) {
        return as_number(left) < as_number(right);
    }
    // String comparison
    if (std::holds_alternative<std::string>(left) && std::holds_alternative<std::string>(right)) {
        return std::get<std::string>(left) < std::get<std::string>(right);
    }
    throw std::runtime_error("cannot compare these types");
}

inline bool less_than_or_equal(const Value& left, const Value& right) {
    return less_than(left, right) || equal(left, right);
}

inline bool greater_than(const Value& left, const Value& right) {
    return less_than(right, left);
}

inline bool greater_than_or_equal(const Value& left, const Value& right) {
    return less_than(right, left) || equal(left, right);
}

// ============================================================================
// Array Operations
// ============================================================================

inline Value make_array(std::initializer_list<Value> items) {
    return std::make_shared<Array>(std::vector<Value>(items));
}

inline Value array_index(const Value& arr, const Value& idx) {
    auto index = as_int(idx);
    if (auto* a = std::get_if<std::shared_ptr<Array>>(&arr)) {
        if (index < 0 || static_cast<size_t>(index) >= (*a)->items.size()) {
            throw std::runtime_error("index out of range");
        }
        return (*a)->items[index];
    }
    if (auto* t = std::get_if<std::shared_ptr<Tuple>>(&arr)) {
        if (index < 0 || static_cast<size_t>(index) >= (*t)->items.size()) {
            throw std::runtime_error("index out of range");
        }
        return (*t)->items[index];
    }
    throw std::runtime_error("expected array or tuple");
}

inline Value array_length(const Value& arr) {
    if (auto* a = std::get_if<std::shared_ptr<Array>>(&arr)) {
        return static_cast<int64_t>((*a)->items.size());
    }
    if (auto* t = std::get_if<std::shared_ptr<Tuple>>(&arr)) {
        return static_cast<int64_t>((*t)->items.size());
    }
    throw std::runtime_error("expected array or tuple");
}

inline void array_set_index(const Value& arr, const Value& idx, const Value& val) {
    auto index = as_int(idx);
    auto a = as_array(arr);
    if (index < 0 || static_cast<size_t>(index) >= a->items.size()) {
        throw std::runtime_error("index out of range");
    }
    a->items[index] = val;
}

inline void array_push(const Value& arr, const Value& val) {
    auto a = as_array(arr);
    a->items.push_back(val);
}

inline Value array_slice(const Value& arr, const Value& start, const Value& end) {
    auto s = as_int(start);
    auto e = as_int(end);

    if (auto* a = std::get_if<std::shared_ptr<Array>>(&arr)) {
        auto size = static_cast<int64_t>((*a)->items.size());
        if (s < 0 || e < 0 || s > size || e > size) {
            throw std::runtime_error("slice out of range");
        }
        auto result = std::make_shared<Array>();
        for (int64_t i = s; i < e; ++i) {
            result->items.push_back((*a)->items[i]);
        }
        return result;
    }
    if (auto* t = std::get_if<std::shared_ptr<Tuple>>(&arr)) {
        auto size = static_cast<int64_t>((*t)->items.size());
        if (s < 0 || e < 0 || s > size || e > size) {
            throw std::runtime_error("slice out of range");
        }
        auto result = std::make_shared<Array>();
        for (int64_t i = s; i < e; ++i) {
            result->items.push_back((*t)->items[i]);
        }
        return result;
    }
    throw std::runtime_error("expected array or tuple");
}

// ============================================================================
// Tuple Operations
// ============================================================================

inline Value make_tuple(std::initializer_list<Value> items) {
    return std::make_shared<Tuple>(std::vector<Value>(items));
}

// ============================================================================
// Map Operations
// ============================================================================

inline Value make_map(std::initializer_list<std::pair<Value, Value>> items) {
    auto m = std::make_shared<Map>();
    for (const auto& [k, v] : items) {
        auto key_str = serialize_value(k);
        auto it = m->index.find(key_str);
        if (it != m->index.end()) {
            // Update existing
            m->items[it->second].second = v;
        } else {
            // Insert new
            m->index[key_str] = m->items.size();
            m->items.emplace_back(k, v);
        }
    }
    return m;
}

inline Value map_get(const Value& map, const Value& key) {
    auto m = as_map(map);
    auto key_str = serialize_value(key);
    auto it = m->index.find(key_str);
    if (it == m->index.end()) {
        return nullptr;
    }
    return m->items[it->second].second;
}

inline Value map_get_default(const Value& map, const Value& key, const Value& def) {
    auto m = as_map(map);
    auto key_str = serialize_value(key);
    auto it = m->index.find(key_str);
    if (it == m->index.end()) {
        return def;
    }
    return m->items[it->second].second;
}

inline void map_set(const Value& map, const Value& key, const Value& val) {
    auto m = as_map(map);
    auto key_str = serialize_value(key);
    auto it = m->index.find(key_str);
    if (it != m->index.end()) {
        // Update existing, preserving order
        m->items[it->second].second = val;
    } else {
        // Insert new at end
        m->index[key_str] = m->items.size();
        m->items.emplace_back(key, val);
    }
}

inline Value map_keys(const Value& map) {
    auto m = as_map(map);
    auto result = std::make_shared<Array>();
    for (const auto& [k, v] : m->items) {
        result->items.push_back(k);
    }
    return result;
}

// ============================================================================
// Set Operations
// ============================================================================

inline Value make_set(std::initializer_list<Value> items) {
    auto s = std::make_shared<Set>();
    for (const auto& item : items) {
        auto key_str = serialize_value(item);
        if (s->index.find(key_str) == s->index.end()) {
            s->index.insert(key_str);
            s->items.push_back(item);
        }
    }
    return s;
}

inline Value set_has(const Value& set, const Value& item) {
    auto s = as_set(set);
    auto key_str = serialize_value(item);
    return s->index.find(key_str) != s->index.end();
}

inline void set_add(const Value& set, const Value& item) {
    auto s = as_set(set);
    auto key_str = serialize_value(item);
    if (s->index.find(key_str) == s->index.end()) {
        s->index.insert(key_str);
        s->items.push_back(item);
    }
}

inline void set_remove(const Value& set, const Value& item) {
    auto s = as_set(set);
    auto key_str = serialize_value(item);
    auto it = s->index.find(key_str);
    if (it != s->index.end()) {
        s->index.erase(it);
        // Remove from items vector
        s->items.erase(std::remove_if(s->items.begin(), s->items.end(),
            [&key_str](const Value& v) { return serialize_value(v) == key_str; }),
            s->items.end());
    }
}

inline Value set_size(const Value& set) {
    auto s = as_set(set);
    return static_cast<int64_t>(s->items.size());
}

// ============================================================================
// Record Operations
// ============================================================================

inline Value make_record(std::initializer_list<std::pair<std::string, Value>> fields) {
    auto r = std::make_shared<Record>();
    for (const auto& [k, v] : fields) {
        r->fields[k] = v;
    }
    return r;
}

inline Value record_get_field(const Value& rec, const std::string& name) {
    auto r = as_record(rec);
    auto it = r->fields.find(name);
    if (it == r->fields.end()) {
        throw std::runtime_error("field '" + name + "' not found");
    }
    return it->second;
}

inline void record_set_field(const Value& rec, const std::string& name, const Value& val) {
    auto r = as_record(rec);
    r->fields[name] = val;
}

// ============================================================================
// Deque Operations
// ============================================================================

inline Value deque_new() {
    return std::make_shared<Deque>();
}

inline Value deque_size(const Value& dq) {
    auto d = as_deque(dq);
    return static_cast<int64_t>(d->items.size());
}

inline void deque_push_back(const Value& dq, const Value& val) {
    auto d = as_deque(dq);
    d->items.push_back(val);
}

inline void deque_push_front(const Value& dq, const Value& val) {
    auto d = as_deque(dq);
    d->items.push_front(val);
}

inline Value deque_pop_front(const Value& dq) {
    auto d = as_deque(dq);
    if (d->items.empty()) {
        throw std::runtime_error("cannot pop from empty deque");
    }
    Value result = d->items.front();
    d->items.pop_front();
    return result;
}

inline Value deque_pop_back(const Value& dq) {
    auto d = as_deque(dq);
    if (d->items.empty()) {
        throw std::runtime_error("cannot pop from empty deque");
    }
    Value result = d->items.back();
    d->items.pop_back();
    return result;
}

// ============================================================================
// Heap Operations
// ============================================================================

inline Value heap_new() {
    return std::make_shared<Heap>();
}

inline Value heap_size(const Value& hp) {
    auto h = as_heap(hp);
    return static_cast<int64_t>(h->pq.size());
}

inline Value heap_peek(const Value& hp) {
    auto h = as_heap(hp);
    if (h->pq.empty()) {
        throw std::runtime_error("cannot peek empty heap");
    }
    return h->pq.top().value;
}

inline void heap_push(const Value& hp, const Value& priority, const Value& val) {
    auto h = as_heap(hp);
    h->pq.push({as_number(priority), h->counter++, val});
}

inline Value heap_pop(const Value& hp) {
    auto h = as_heap(hp);
    if (h->pq.empty()) {
        throw std::runtime_error("cannot pop empty heap");
    }
    Value result = h->pq.top().value;
    h->pq.pop();
    return result;
}

// ============================================================================
// String Operations
// ============================================================================

inline Value string_length(const Value& str) {
    auto s = std::get<std::string>(str);
    return static_cast<int64_t>(s.size());
}

inline Value string_substring(const Value& str, const Value& start, const Value& end) {
    auto s = std::get<std::string>(str);
    auto st = as_int(start);
    auto en = as_int(end);
    auto len = static_cast<int64_t>(s.size());
    if (st < 0 || en < 0 || st > len || en > len) {
        throw std::runtime_error("substring out of range");
    }
    return s.substr(st, en - st);
}

inline Value string_char_at(const Value& str, const Value& idx) {
    auto s = std::get<std::string>(str);
    auto i = as_int(idx);
    if (i < 0 || static_cast<size_t>(i) >= s.size()) {
        throw std::runtime_error("index out of range");
    }
    return std::string(1, s[i]);
}

inline Value string_join(const Value& sep, const Value& items) {
    auto separator = std::get<std::string>(sep);
    auto arr = as_array(items);
    std::string result;
    for (size_t i = 0; i < arr->items.size(); ++i) {
        if (i > 0) result += separator;
        result += as_string(arr->items[i]);
    }
    return result;
}

inline Value string_split(const Value& str, const Value& delim) {
    auto s = std::get<std::string>(str);
    auto d = std::get<std::string>(delim);
    auto result = std::make_shared<Array>();

    if (d.empty()) {
        // Split into characters
        for (char c : s) {
            result->items.push_back(std::string(1, c));
        }
    } else {
        size_t pos = 0;
        size_t prev = 0;
        while ((pos = s.find(d, prev)) != std::string::npos) {
            result->items.push_back(s.substr(prev, pos - prev));
            prev = pos + d.size();
        }
        result->items.push_back(s.substr(prev));
    }
    return result;
}

inline Value string_trim(const Value& str) {
    auto s = std::get<std::string>(str);
    auto start = s.find_first_not_of(" \t\n\r\f\v");
    if (start == std::string::npos) return std::string("");
    auto end = s.find_last_not_of(" \t\n\r\f\v");
    return s.substr(start, end - start + 1);
}

inline Value string_upper(const Value& str) {
    auto s = std::get<std::string>(str);
    std::transform(s.begin(), s.end(), s.begin(), ::toupper);
    return s;
}

inline Value string_lower(const Value& str) {
    auto s = std::get<std::string>(str);
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    return s;
}

inline Value string_starts_with(const Value& str, const Value& prefix) {
    auto s = std::get<std::string>(str);
    auto p = std::get<std::string>(prefix);
    if (p.size() > s.size()) return false;
    return s.compare(0, p.size(), p) == 0;
}

inline Value string_ends_with(const Value& str, const Value& suffix) {
    auto s = std::get<std::string>(str);
    auto suf = std::get<std::string>(suffix);
    if (suf.size() > s.size()) return false;
    return s.compare(s.size() - suf.size(), suf.size(), suf) == 0;
}

inline Value string_contains(const Value& str, const Value& sub) {
    auto s = std::get<std::string>(str);
    auto substring = std::get<std::string>(sub);
    return s.find(substring) != std::string::npos;
}

inline Value string_replace(const Value& str, const Value& old_str, const Value& new_str) {
    auto s = std::get<std::string>(str);
    auto old_s = std::get<std::string>(old_str);
    auto new_s = std::get<std::string>(new_str);

    if (old_s.empty()) return s;

    std::string result;
    size_t pos = 0;
    size_t prev = 0;
    while ((pos = s.find(old_s, prev)) != std::string::npos) {
        result += s.substr(prev, pos - prev);
        result += new_s;
        prev = pos + old_s.size();
    }
    result += s.substr(prev);
    return result;
}

// ============================================================================
// Math Operations
// ============================================================================

inline Value math_sin(const Value& x) { return std::sin(as_number(x)); }
inline Value math_cos(const Value& x) { return std::cos(as_number(x)); }
inline Value math_tan(const Value& x) { return std::tan(as_number(x)); }
inline Value math_sqrt(const Value& x) { return std::sqrt(as_number(x)); }
inline Value math_log(const Value& x) { return std::log(as_number(x)); }
inline Value math_exp(const Value& x) { return std::exp(as_number(x)); }

inline Value math_floor(const Value& x) {
    double v = as_number(x);
    return static_cast<int64_t>(std::floor(v));
}

inline Value math_ceil(const Value& x) {
    double v = as_number(x);
    return static_cast<int64_t>(std::ceil(v));
}

inline Value math_abs(const Value& x) {
    if (auto* i = std::get_if<int64_t>(&x)) {
        return std::abs(*i);
    }
    return std::abs(as_number(x));
}

inline Value math_pow(const Value& base, const Value& exp) {
    return std::pow(as_number(base), as_number(exp));
}

inline Value math_pi() { return M_PI; }
inline Value math_e() { return M_E; }

// ============================================================================
// Regex Operations
// ============================================================================

inline std::regex_constants::syntax_option_type parse_regex_flags(const std::string& flags) {
    auto result = std::regex_constants::ECMAScript;
    for (char c : flags) {
        if (c == 'i') result |= std::regex_constants::icase;
    }
    return result;
}

inline Value regex_match(const Value& str, const Value& pattern, const Value& flags = std::string("")) {
    auto s = std::get<std::string>(str);
    auto p = std::get<std::string>(pattern);
    auto f = std::get<std::string>(flags);
    try {
        std::regex re(p, parse_regex_flags(f));
        return std::regex_search(s, re);
    } catch (const std::regex_error& e) {
        throw std::runtime_error(std::string("invalid regex: ") + e.what());
    }
}

inline Value regex_find_all(const Value& str, const Value& pattern, const Value& flags = std::string("")) {
    auto s = std::get<std::string>(str);
    auto p = std::get<std::string>(pattern);
    auto f = std::get<std::string>(flags);

    auto result = std::make_shared<Array>();
    try {
        std::regex re(p, parse_regex_flags(f));
        std::sregex_iterator it(s.begin(), s.end(), re);
        std::sregex_iterator end;
        for (; it != end; ++it) {
            result->items.push_back(it->str());
        }
    } catch (const std::regex_error& e) {
        throw std::runtime_error(std::string("invalid regex: ") + e.what());
    }
    return result;
}

inline Value regex_replace(const Value& str, const Value& pattern, const Value& replacement,
                          const Value& flags = std::string("")) {
    auto s = std::get<std::string>(str);
    auto p = std::get<std::string>(pattern);
    auto r = std::get<std::string>(replacement);
    auto f = std::get<std::string>(flags);

    try {
        std::regex re(p, parse_regex_flags(f));
        return std::regex_replace(s, re, r);
    } catch (const std::regex_error& e) {
        throw std::runtime_error(std::string("invalid regex: ") + e.what());
    }
}

inline Value regex_split(const Value& str, const Value& pattern, const Value& flags = std::string("")) {
    auto s = std::get<std::string>(str);
    auto p = std::get<std::string>(pattern);
    auto f = std::get<std::string>(flags);

    auto result = std::make_shared<Array>();
    try {
        std::regex re(p, parse_regex_flags(f));
        std::sregex_token_iterator it(s.begin(), s.end(), re, -1);
        std::sregex_token_iterator end;
        for (; it != end; ++it) {
            result->items.push_back(std::string(*it));
        }
    } catch (const std::regex_error& e) {
        throw std::runtime_error(std::string("invalid regex: ") + e.what());
    }
    return result;
}

// ============================================================================
// JSON Operations (requires nlohmann/json.hpp to be included BEFORE this header)
// ============================================================================

#ifdef NLOHMANN_JSON_HPP

inline nlohmann::json value_to_json(const Value& v);
inline Value json_to_value(const nlohmann::json& j);

inline nlohmann::json value_to_json(const Value& v) {
    return std::visit([](auto&& arg) -> nlohmann::json {
        using T = std::decay_t<decltype(arg)>;
        if constexpr (std::is_same_v<T, std::nullptr_t>) {
            return nullptr;
        } else if constexpr (std::is_same_v<T, bool>) {
            return arg;
        } else if constexpr (std::is_same_v<T, int64_t>) {
            return arg;
        } else if constexpr (std::is_same_v<T, double>) {
            return arg;
        } else if constexpr (std::is_same_v<T, std::string>) {
            return arg;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Array>>) {
            nlohmann::json arr = nlohmann::json::array();
            for (const auto& item : arg->items) {
                arr.push_back(value_to_json(item));
            }
            return arr;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Tuple>>) {
            nlohmann::json arr = nlohmann::json::array();
            for (const auto& item : arg->items) {
                arr.push_back(value_to_json(item));
            }
            return arr;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Map>>) {
            nlohmann::json obj = nlohmann::json::object();
            for (const auto& [k, v] : arg->items) {
                // JSON keys must be strings
                obj[as_string(k)] = value_to_json(v);
            }
            return obj;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Record>>) {
            nlohmann::json obj = nlohmann::json::object();
            for (const auto& [k, v] : arg->fields) {
                obj[k] = value_to_json(v);
            }
            return obj;
        } else if constexpr (std::is_same_v<T, std::shared_ptr<Set>>) {
            nlohmann::json arr = nlohmann::json::array();
            for (const auto& item : arg->items) {
                arr.push_back(value_to_json(item));
            }
            return arr;
        } else {
            throw std::runtime_error("cannot convert to JSON");
        }
    }, v);
}

inline Value json_to_value(const nlohmann::json& j) {
    if (j.is_null()) return nullptr;
    if (j.is_boolean()) return j.get<bool>();
    if (j.is_number_integer()) return j.get<int64_t>();
    if (j.is_number_float()) return j.get<double>();
    if (j.is_string()) return j.get<std::string>();
    if (j.is_array()) {
        auto arr = std::make_shared<Array>();
        for (const auto& item : j) {
            arr->items.push_back(json_to_value(item));
        }
        return arr;
    }
    if (j.is_object()) {
        auto map = std::make_shared<Map>();
        for (auto& [k, v] : j.items()) {
            map->index[k] = map->items.size();
            map->items.emplace_back(std::string(k), json_to_value(v));
        }
        return map;
    }
    throw std::runtime_error("unsupported JSON type");
}

inline Value json_parse(const Value& str) {
    auto s = std::get<std::string>(str);
    try {
        return json_to_value(nlohmann::json::parse(s));
    } catch (const nlohmann::json::parse_error& e) {
        throw std::runtime_error(std::string("invalid JSON: ") + e.what());
    }
}

inline Value json_stringify(const Value& v, bool pretty = false) {
    auto j = value_to_json(v);
    if (pretty) {
        return j.dump(2);
    }
    return j.dump();
}

#endif // NLOHMANN_JSON_HPP

// ============================================================================
// Logical Not
// ============================================================================

inline Value logical_not(const Value& v) {
    return !is_truthy(v);
}

// ============================================================================
// Range Iterator Helper
// ============================================================================

class Range {
public:
    int64_t start_, end_;
    bool inclusive_;

    Range(int64_t start, int64_t end, bool inclusive = false)
        : start_(start), end_(end), inclusive_(inclusive) {}

    class Iterator {
    public:
        int64_t current_;
        explicit Iterator(int64_t v) : current_(v) {}
        int64_t operator*() const { return current_; }
        Iterator& operator++() { ++current_; return *this; }
        bool operator!=(const Iterator& other) const { return current_ != other.current_; }
    };

    Iterator begin() const { return Iterator(start_); }
    Iterator end() const { return Iterator(inclusive_ ? end_ + 1 : end_); }
};

} // namespace coreil

#endif // COREIL_RUNTIME_HPP
