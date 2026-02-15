/**
 * Core IL Runtime Library for AssemblyScript
 *
 * This runtime provides dynamic typing support for Core IL programs compiled
 * to WebAssembly via AssemblyScript. It implements:
 *
 * - Value class with type tags for dynamic typing
 * - OrderedMap (preserves insertion order like Python dict)
 * - OrderedSet (set with insertion order)
 * - Heap (min-heap with stable ordering)
 * - Deque (double-ended queue)
 * - Host bindings for I/O
 *
 * Version: Core IL v1.8
 */

// ============================================================================
// Host Bindings
// ============================================================================

@external("env", "print")
declare function __host_print(s: string): void;

// ============================================================================
// Value Type Enum
// ============================================================================

export enum ValueType {
  NULL,
  BOOL,
  INT,
  FLOAT,
  STRING,
  ARRAY,
  MAP,
  SET,
  TUPLE,
  RECORD,
  DEQUE,
  HEAP,
}

// ============================================================================
// Value Class - Dynamic Typing
// ============================================================================

export class Value {
  type: ValueType;

  // Storage for different types
  private _bool: bool = false;
  private _int: i64 = 0;
  private _float: f64 = 0.0;
  private _string: string = "";
  private _array: Value[] | null = null;
  private _map: OrderedMap | null = null;
  private _set: OrderedSet | null = null;
  private _record: OrderedMap | null = null;
  private _deque: Deque | null = null;
  private _heap: Heap | null = null;

  constructor(type: ValueType) {
    this.type = type;
  }

  // Factory methods
  static null(): Value {
    return new Value(ValueType.NULL);
  }

  static fromBool(b: bool): Value {
    const v = new Value(ValueType.BOOL);
    v._bool = b;
    return v;
  }

  static fromInt(i: i64): Value {
    const v = new Value(ValueType.INT);
    v._int = i;
    return v;
  }

  static fromFloat(f: f64): Value {
    const v = new Value(ValueType.FLOAT);
    v._float = f;
    return v;
  }

  static fromString(s: string): Value {
    const v = new Value(ValueType.STRING);
    v._string = s;
    return v;
  }

  static fromArray(arr: Value[]): Value {
    const v = new Value(ValueType.ARRAY);
    v._array = arr;
    return v;
  }

  static fromMap(m: OrderedMap): Value {
    const v = new Value(ValueType.MAP);
    v._map = m;
    return v;
  }

  static fromSet(s: OrderedSet): Value {
    const v = new Value(ValueType.SET);
    v._set = s;
    return v;
  }

  static fromTuple(items: Value[]): Value {
    const v = new Value(ValueType.TUPLE);
    v._array = items;
    return v;
  }

  static fromRecord(r: OrderedMap): Value {
    const v = new Value(ValueType.RECORD);
    v._record = r;
    return v;
  }

  static fromDeque(d: Deque): Value {
    const v = new Value(ValueType.DEQUE);
    v._deque = d;
    return v;
  }

  static fromHeap(h: Heap): Value {
    const v = new Value(ValueType.HEAP);
    v._heap = h;
    return v;
  }

  // Getters with type checking
  asBool(): bool {
    if (this.type != ValueType.BOOL) {
      throw new Error("Expected BOOL, got " + this.typeName());
    }
    return this._bool;
  }

  asInt(): i64 {
    if (this.type == ValueType.INT) return this._int;
    if (this.type == ValueType.FLOAT) return i64(this._float);
    throw new Error("Expected INT, got " + this.typeName());
  }

  asFloat(): f64 {
    if (this.type == ValueType.FLOAT) return this._float;
    if (this.type == ValueType.INT) return f64(this._int);
    throw new Error("Expected FLOAT, got " + this.typeName());
  }

  asString(): string {
    if (this.type != ValueType.STRING) {
      throw new Error("Expected STRING, got " + this.typeName());
    }
    return this._string;
  }

  asArray(): Value[] {
    if (this.type != ValueType.ARRAY) {
      throw new Error("Expected ARRAY, got " + this.typeName());
    }
    return this._array!;
  }

  asMap(): OrderedMap {
    if (this.type != ValueType.MAP) {
      throw new Error("Expected MAP, got " + this.typeName());
    }
    return this._map!;
  }

  asSet(): OrderedSet {
    if (this.type != ValueType.SET) {
      throw new Error("Expected SET, got " + this.typeName());
    }
    return this._set!;
  }

  asTuple(): Value[] {
    if (this.type != ValueType.TUPLE) {
      throw new Error("Expected TUPLE, got " + this.typeName());
    }
    return this._array!;
  }

  asRecord(): OrderedMap {
    if (this.type != ValueType.RECORD) {
      throw new Error("Expected RECORD, got " + this.typeName());
    }
    return this._record!;
  }

  asDeque(): Deque {
    if (this.type != ValueType.DEQUE) {
      throw new Error("Expected DEQUE, got " + this.typeName());
    }
    return this._deque!;
  }

  asHeap(): Heap {
    if (this.type != ValueType.HEAP) {
      throw new Error("Expected HEAP, got " + this.typeName());
    }
    return this._heap!;
  }

  // Check if value is truthy (for conditionals)
  isTruthy(): bool {
    switch (this.type) {
      case ValueType.NULL:
        return false;
      case ValueType.BOOL:
        return this._bool;
      case ValueType.INT:
        return this._int != 0;
      case ValueType.FLOAT:
        return this._float != 0.0;
      case ValueType.STRING:
        return this._string.length > 0;
      case ValueType.ARRAY:
      case ValueType.TUPLE:
        return this._array!.length > 0;
      case ValueType.MAP:
      case ValueType.RECORD:
        return this._map != null ? this._map!.size() > 0 : this._record!.size() > 0;
      case ValueType.SET:
        return this._set!.size() > 0;
      case ValueType.DEQUE:
        return this._deque!.size() > 0;
      case ValueType.HEAP:
        return this._heap!.size() > 0;
      default:
        return false;
    }
  }

  typeName(): string {
    switch (this.type) {
      case ValueType.NULL: return "NULL";
      case ValueType.BOOL: return "BOOL";
      case ValueType.INT: return "INT";
      case ValueType.FLOAT: return "FLOAT";
      case ValueType.STRING: return "STRING";
      case ValueType.ARRAY: return "ARRAY";
      case ValueType.MAP: return "MAP";
      case ValueType.SET: return "SET";
      case ValueType.TUPLE: return "TUPLE";
      case ValueType.RECORD: return "RECORD";
      case ValueType.DEQUE: return "DEQUE";
      case ValueType.HEAP: return "HEAP";
      default: return "UNKNOWN";
    }
  }

  // Arithmetic operations
  add(other: Value): Value {
    // String concatenation
    if (this.type == ValueType.STRING && other.type == ValueType.STRING) {
      return Value.fromString(this._string + other._string);
    }

    // Numeric addition
    const isFloat = this.type == ValueType.FLOAT || other.type == ValueType.FLOAT;
    if (isFloat) {
      return Value.fromFloat(this.asFloat() + other.asFloat());
    }
    return Value.fromInt(this.asInt() + other.asInt());
  }

  sub(other: Value): Value {
    const isFloat = this.type == ValueType.FLOAT || other.type == ValueType.FLOAT;
    if (isFloat) {
      return Value.fromFloat(this.asFloat() - other.asFloat());
    }
    return Value.fromInt(this.asInt() - other.asInt());
  }

  mul(other: Value): Value {
    const isFloat = this.type == ValueType.FLOAT || other.type == ValueType.FLOAT;
    if (isFloat) {
      return Value.fromFloat(this.asFloat() * other.asFloat());
    }
    return Value.fromInt(this.asInt() * other.asInt());
  }

  div(other: Value): Value {
    // Division always returns float (like Python 3)
    return Value.fromFloat(this.asFloat() / other.asFloat());
  }

  floorDiv(other: Value): Value {
    // Integer division
    const result = Math.floor(this.asFloat() / other.asFloat());
    return Value.fromInt(i64(result));
  }

  mod(other: Value): Value {
    // Python-style modulo (always returns positive)
    const a = this.asInt();
    const b = other.asInt();
    return Value.fromInt(((a % b) + b) % b);
  }

  // Comparison operations
  eq(other: Value): Value {
    return Value.fromBool(this.equals(other));
  }

  ne(other: Value): Value {
    return Value.fromBool(!this.equals(other));
  }

  lt(other: Value): Value {
    return Value.fromBool(this.compare(other) < 0);
  }

  le(other: Value): Value {
    return Value.fromBool(this.compare(other) <= 0);
  }

  gt(other: Value): Value {
    return Value.fromBool(this.compare(other) > 0);
  }

  ge(other: Value): Value {
    return Value.fromBool(this.compare(other) >= 0);
  }

  // Logical operations (short-circuit evaluated at call site)
  not(): Value {
    return Value.fromBool(!this.isTruthy());
  }

  // Deep equality check
  equals(other: Value): bool {
    if (this.type != other.type) return false;

    switch (this.type) {
      case ValueType.NULL:
        return true;
      case ValueType.BOOL:
        return this._bool == other._bool;
      case ValueType.INT:
        return this._int == other._int;
      case ValueType.FLOAT:
        return this._float == other._float;
      case ValueType.STRING:
        return this._string == other._string;
      case ValueType.ARRAY:
      case ValueType.TUPLE:
        const arr1 = this._array!;
        const arr2 = other._array!;
        if (arr1.length != arr2.length) return false;
        for (let i = 0; i < arr1.length; i++) {
          if (!arr1[i].equals(arr2[i])) return false;
        }
        return true;
      case ValueType.MAP:
      case ValueType.RECORD:
        const m1 = this.type == ValueType.MAP ? this._map! : this._record!;
        const m2 = other.type == ValueType.MAP ? other._map! : other._record!;
        return m1.equals(m2);
      case ValueType.SET:
        return this._set!.equals(other._set!);
      default:
        return false;
    }
  }

  // Comparison for ordering
  compare(other: Value): i32 {
    // Numeric comparison
    if ((this.type == ValueType.INT || this.type == ValueType.FLOAT) &&
        (other.type == ValueType.INT || other.type == ValueType.FLOAT)) {
      const a = this.asFloat();
      const b = other.asFloat();
      if (a < b) return -1;
      if (a > b) return 1;
      return 0;
    }

    // String comparison
    if (this.type == ValueType.STRING && other.type == ValueType.STRING) {
      if (this._string < other._string) return -1;
      if (this._string > other._string) return 1;
      return 0;
    }

    throw new Error("Cannot compare " + this.typeName() + " with " + other.typeName());
  }

  // Convert to string for printing
  toString(): string {
    switch (this.type) {
      case ValueType.NULL:
        return "None";
      case ValueType.BOOL:
        return this._bool ? "True" : "False";
      case ValueType.INT:
        return this._int.toString();
      case ValueType.FLOAT:
        // Python-style float formatting
        const f = this._float;
        if (Math.floor(f) == f && f < 1e15 && f > -1e15) {
          return f.toString() + ".0";
        }
        return f.toString();
      case ValueType.STRING:
        return this._string;
      case ValueType.ARRAY:
      case ValueType.TUPLE:
        const arr = this._array!;
        const items: string[] = [];
        for (let i = 0; i < arr.length; i++) {
          items.push(arr[i].toRepr());
        }
        if (this.type == ValueType.TUPLE) {
          if (items.length == 1) {
            return "(" + items[0] + ",)";
          }
          return "(" + items.join(", ") + ")";
        }
        return "[" + items.join(", ") + "]";
      case ValueType.MAP:
        return this._map!.toString();
      case ValueType.RECORD:
        return this._record!.toString();
      case ValueType.SET:
        return this._set!.toString();
      case ValueType.DEQUE:
        return this._deque!.toString();
      case ValueType.HEAP:
        return this._heap!.toString();
      default:
        return "<unknown>";
    }
  }

  // String representation (with quotes for strings)
  toRepr(): string {
    if (this.type == ValueType.STRING) {
      return "'" + this._string + "'";
    }
    return this.toString();
  }

  // Create hashable key for maps/sets
  toKey(): string {
    switch (this.type) {
      case ValueType.NULL:
        return "N:";
      case ValueType.BOOL:
        return "B:" + (this._bool ? "1" : "0");
      case ValueType.INT:
        return "I:" + this._int.toString();
      case ValueType.FLOAT:
        return "F:" + this._float.toString();
      case ValueType.STRING:
        return "S:" + this._string;
      case ValueType.TUPLE:
        const items: string[] = [];
        const arr = this._array!;
        for (let i = 0; i < arr.length; i++) {
          items.push(arr[i].toKey());
        }
        return "T:(" + items.join(",") + ")";
      default:
        throw new Error("Type " + this.typeName() + " is not hashable");
    }
  }

  // Index operation (arrays, strings, tuples)
  index(idx: Value): Value {
    let i = idx.asInt();

    if (this.type == ValueType.ARRAY || this.type == ValueType.TUPLE) {
      const arr = this._array!;
      // Python-style negative indexing
      if (i < 0) i = i64(arr.length) + i;
      if (i < 0 || i >= arr.length) {
        throw new Error("Index out of range");
      }
      return arr[i32(i)];
    }

    if (this.type == ValueType.STRING) {
      const s = this._string;
      if (i < 0) i = i64(s.length) + i;
      if (i < 0 || i >= s.length) {
        throw new Error("String index out of range");
      }
      return Value.fromString(s.charAt(i32(i)));
    }

    throw new Error("Cannot index " + this.typeName());
  }

  // SetIndex operation
  setIndex(idx: Value, val: Value): void {
    if (this.type != ValueType.ARRAY) {
      throw new Error("Cannot setIndex on " + this.typeName());
    }
    let i = idx.asInt();
    const arr = this._array!;
    if (i < 0) i = i64(arr.length) + i;
    if (i < 0 || i >= arr.length) {
      throw new Error("Index out of range");
    }
    arr[i32(i)] = val;
  }

  // Slice operation
  slice(start: Value, end: Value): Value {
    const s = start.asInt();
    const e = end.asInt();

    if (this.type == ValueType.ARRAY) {
      const arr = this._array!;
      const result: Value[] = [];
      const startIdx = i32(s < 0 ? Math.max(0, arr.length + s) : Math.min(arr.length, s));
      const endIdx = i32(e < 0 ? Math.max(0, arr.length + e) : Math.min(arr.length, e));
      for (let i = startIdx; i < endIdx; i++) {
        result.push(arr[i]);
      }
      return Value.fromArray(result);
    }

    if (this.type == ValueType.STRING) {
      const str = this._string;
      const startIdx = i32(s < 0 ? Math.max(0, str.length + s) : Math.min(str.length, s));
      const endIdx = i32(e < 0 ? Math.max(0, str.length + e) : Math.min(str.length, e));
      return Value.fromString(str.substring(startIdx, endIdx));
    }

    throw new Error("Cannot slice " + this.typeName());
  }

  // Length operation
  length(): Value {
    if (this.type == ValueType.ARRAY || this.type == ValueType.TUPLE) {
      return Value.fromInt(this._array!.length);
    }
    if (this.type == ValueType.STRING) {
      return Value.fromInt(this._string.length);
    }
    if (this.type == ValueType.MAP) {
      return Value.fromInt(this._map!.size());
    }
    if (this.type == ValueType.RECORD) {
      return Value.fromInt(this._record!.size());
    }
    if (this.type == ValueType.SET) {
      return Value.fromInt(this._set!.size());
    }
    throw new Error("Cannot get length of " + this.typeName());
  }

  // Push operation (arrays)
  push(val: Value): void {
    if (this.type != ValueType.ARRAY) {
      throw new Error("Cannot push to " + this.typeName());
    }
    this._array!.push(val);
  }

  // Type conversions (v1.9)
  toInt(): Value {
    if (this.type == ValueType.INT) return Value.fromInt(this._int);
    if (this.type == ValueType.FLOAT) return Value.fromInt(i64(this._float));
    if (this.type == ValueType.STRING) {
      const n = I64.parseInt(this._string);
      return Value.fromInt(n);
    }
    throw new Error("runtime error: cannot convert " + this.typeName() + " to int");
  }

  toFloat(): Value {
    if (this.type == ValueType.FLOAT) return Value.fromFloat(this._float);
    if (this.type == ValueType.INT) return Value.fromFloat(f64(this._int));
    if (this.type == ValueType.STRING) {
      const f = F64.parseFloat(this._string);
      return Value.fromFloat(f);
    }
    throw new Error("runtime error: cannot convert " + this.typeName() + " to float");
  }

  toStringConvert(): Value {
    return Value.fromString(this.toString());
  }
}

// ============================================================================
// OrderedMap - Preserves insertion order like Python dict
// ============================================================================

export class OrderedMap {
  private keys_: string[] = [];
  private values_: Map<string, Value> = new Map();

  size(): i32 {
    return this.keys_.length;
  }

  has(key: Value): bool {
    return this.values_.has(key.toKey());
  }

  get(key: Value): Value {
    const k = key.toKey();
    if (!this.values_.has(k)) {
      return Value.null();
    }
    return this.values_.get(k);
  }

  getDefault(key: Value, def: Value): Value {
    const k = key.toKey();
    if (!this.values_.has(k)) {
      return def;
    }
    return this.values_.get(k);
  }

  set(key: Value, value: Value): void {
    const k = key.toKey();
    if (!this.values_.has(k)) {
      this.keys_.push(k);
    }
    this.values_.set(k, value);
  }

  delete(key: Value): bool {
    const k = key.toKey();
    if (!this.values_.has(k)) {
      return false;
    }
    this.values_.delete(k);
    const idx = this.keys_.indexOf(k);
    if (idx >= 0) {
      this.keys_.splice(idx, 1);
    }
    return true;
  }

  keys(): Value[] {
    const result: Value[] = [];
    for (let i = 0; i < this.keys_.length; i++) {
      const k = this.keys_[i];
      result.push(this.keyFromString(k));
    }
    return result;
  }

  private keyFromString(k: string): Value {
    // Parse key back to Value
    if (k.startsWith("N:")) return Value.null();
    if (k.startsWith("B:")) return Value.fromBool(k.charAt(2) == "1");
    if (k.startsWith("I:")) return Value.fromInt(I64.parseInt(k.substring(2)));
    if (k.startsWith("F:")) return Value.fromFloat(F64.parseFloat(k.substring(2)));
    if (k.startsWith("S:")) return Value.fromString(k.substring(2));
    // Tuples are more complex, store original key
    return Value.fromString(k);
  }

  equals(other: OrderedMap): bool {
    if (this.size() != other.size()) return false;
    for (let i = 0; i < this.keys_.length; i++) {
      const k = this.keys_[i];
      if (!other.values_.has(k)) return false;
      if (!this.values_.get(k).equals(other.values_.get(k))) return false;
    }
    return true;
  }

  toString(): string {
    const pairs: string[] = [];
    for (let i = 0; i < this.keys_.length; i++) {
      const k = this.keys_[i];
      const keyVal = this.keyFromString(k);
      const val = this.values_.get(k);
      pairs.push(keyVal.toRepr() + ": " + val.toRepr());
    }
    return "{" + pairs.join(", ") + "}";
  }
}

// ============================================================================
// OrderedSet - Set with insertion order
// ============================================================================

export class OrderedSet {
  private items_: string[] = [];
  private set_: Set<string> = new Set();

  size(): i32 {
    return this.items_.length;
  }

  has(item: Value): bool {
    return this.set_.has(item.toKey());
  }

  add(item: Value): void {
    const k = item.toKey();
    if (!this.set_.has(k)) {
      this.items_.push(k);
      this.set_.add(k);
    }
  }

  delete(item: Value): bool {
    const k = item.toKey();
    if (!this.set_.has(k)) {
      return false;
    }
    this.set_.delete(k);
    const idx = this.items_.indexOf(k);
    if (idx >= 0) {
      this.items_.splice(idx, 1);
    }
    return true;
  }

  equals(other: OrderedSet): bool {
    if (this.size() != other.size()) return false;
    for (let i = 0; i < this.items_.length; i++) {
      if (!other.set_.has(this.items_[i])) return false;
    }
    return true;
  }

  toString(): string {
    if (this.items_.length == 0) return "set()";
    const items: string[] = [];
    for (let i = 0; i < this.items_.length; i++) {
      items.push(this.items_[i]);
    }
    return "{" + items.join(", ") + "}";
  }
}

// ============================================================================
// Deque - Double-ended queue
// ============================================================================

export class Deque {
  private items_: Value[] = [];

  size(): i32 {
    return this.items_.length;
  }

  pushBack(item: Value): void {
    this.items_.push(item);
  }

  pushFront(item: Value): void {
    this.items_.unshift(item);
  }

  popBack(): Value {
    if (this.items_.length == 0) {
      throw new Error("Deque is empty");
    }
    return this.items_.pop();
  }

  popFront(): Value {
    if (this.items_.length == 0) {
      throw new Error("Deque is empty");
    }
    return this.items_.shift();
  }

  toString(): string {
    const items: string[] = [];
    for (let i = 0; i < this.items_.length; i++) {
      items.push(this.items_[i].toRepr());
    }
    return "deque([" + items.join(", ") + "])";
  }
}

// ============================================================================
// Heap - Min-heap priority queue with stable ordering
// ============================================================================

class HeapEntry {
  priority: f64;
  counter: i64;
  value: Value;

  constructor(priority: f64, counter: i64, value: Value) {
    this.priority = priority;
    this.counter = counter;
    this.value = value;
  }

  compare(other: HeapEntry): i32 {
    if (this.priority < other.priority) return -1;
    if (this.priority > other.priority) return 1;
    if (this.counter < other.counter) return -1;
    if (this.counter > other.counter) return 1;
    return 0;
  }
}

export class Heap {
  private items_: HeapEntry[] = [];
  private counter_: i64 = 0;

  size(): i32 {
    return this.items_.length;
  }

  push(priority: Value, value: Value): void {
    const entry = new HeapEntry(priority.asFloat(), this.counter_++, value);
    this.items_.push(entry);
    this.siftUp(this.items_.length - 1);
  }

  pop(): Value {
    if (this.items_.length == 0) {
      throw new Error("Heap is empty");
    }
    const result = this.items_[0].value;
    const last = this.items_.pop();
    if (this.items_.length > 0) {
      this.items_[0] = last;
      this.siftDown(0);
    }
    return result;
  }

  peek(): Value {
    if (this.items_.length == 0) {
      throw new Error("Heap is empty");
    }
    return this.items_[0].value;
  }

  private siftUp(i: i32): void {
    while (i > 0) {
      const parent = (i - 1) / 2;
      if (this.items_[i].compare(this.items_[parent]) < 0) {
        const tmp = this.items_[i];
        this.items_[i] = this.items_[parent];
        this.items_[parent] = tmp;
        i = parent;
      } else {
        break;
      }
    }
  }

  private siftDown(i: i32): void {
    const n = this.items_.length;
    while (true) {
      let smallest = i;
      const left = 2 * i + 1;
      const right = 2 * i + 2;
      if (left < n && this.items_[left].compare(this.items_[smallest]) < 0) {
        smallest = left;
      }
      if (right < n && this.items_[right].compare(this.items_[smallest]) < 0) {
        smallest = right;
      }
      if (smallest == i) break;
      const tmp = this.items_[i];
      this.items_[i] = this.items_[smallest];
      this.items_[smallest] = tmp;
      i = smallest;
    }
  }

  toString(): string {
    return "<Heap size=" + this.items_.length.toString() + ">";
  }
}

// ============================================================================
// Global Print Function
// ============================================================================

export function print(...args: Value[]): void {
  const parts: string[] = [];
  for (let i = 0; i < args.length; i++) {
    parts.push(args[i].toString());
  }
  __host_print(parts.join(" "));
}

// ============================================================================
// String Operations
// ============================================================================

export function stringLength(s: Value): Value {
  return Value.fromInt(s.asString().length);
}

export function substring(s: Value, start: Value, end: Value): Value {
  const str = s.asString();
  return Value.fromString(str.substring(i32(start.asInt()), i32(end.asInt())));
}

export function charAt(s: Value, idx: Value): Value {
  const str = s.asString();
  const i = i32(idx.asInt());
  return Value.fromString(str.charAt(i));
}

export function join(sep: Value, items: Value): Value {
  const arr = items.asArray();
  const parts: string[] = [];
  for (let i = 0; i < arr.length; i++) {
    parts.push(arr[i].toString());
  }
  return Value.fromString(parts.join(sep.asString()));
}

export function stringSplit(s: Value, delimiter: Value): Value {
  const parts = s.asString().split(delimiter.asString());
  const result: Value[] = [];
  for (let i = 0; i < parts.length; i++) {
    result.push(Value.fromString(parts[i]));
  }
  return Value.fromArray(result);
}

export function stringTrim(s: Value): Value {
  return Value.fromString(s.asString().trim());
}

export function stringUpper(s: Value): Value {
  return Value.fromString(s.asString().toUpperCase());
}

export function stringLower(s: Value): Value {
  return Value.fromString(s.asString().toLowerCase());
}

export function stringStartsWith(s: Value, prefix: Value): Value {
  return Value.fromBool(s.asString().startsWith(prefix.asString()));
}

export function stringEndsWith(s: Value, suffix: Value): Value {
  return Value.fromBool(s.asString().endsWith(suffix.asString()));
}

export function stringContains(s: Value, sub: Value): Value {
  return Value.fromBool(s.asString().includes(sub.asString()));
}

export function stringReplace(s: Value, old: Value, newStr: Value): Value {
  return Value.fromString(s.asString().replaceAll(old.asString(), newStr.asString()));
}

// ============================================================================
// Math Operations
// ============================================================================

export function mathSin(x: Value): Value {
  return Value.fromFloat(Math.sin(x.asFloat()));
}

export function mathCos(x: Value): Value {
  return Value.fromFloat(Math.cos(x.asFloat()));
}

export function mathTan(x: Value): Value {
  return Value.fromFloat(Math.tan(x.asFloat()));
}

export function mathSqrt(x: Value): Value {
  return Value.fromFloat(Math.sqrt(x.asFloat()));
}

export function mathFloor(x: Value): Value {
  return Value.fromInt(i64(Math.floor(x.asFloat())));
}

export function mathCeil(x: Value): Value {
  return Value.fromInt(i64(Math.ceil(x.asFloat())));
}

export function mathAbs(x: Value): Value {
  if (x.type == ValueType.INT) {
    const i = x.asInt();
    return Value.fromInt(i < 0 ? -i : i);
  }
  return Value.fromFloat(Math.abs(x.asFloat()));
}

export function mathLog(x: Value): Value {
  return Value.fromFloat(Math.log(x.asFloat()));
}

export function mathExp(x: Value): Value {
  return Value.fromFloat(Math.exp(x.asFloat()));
}

export function mathPow(base: Value, exp: Value): Value {
  return Value.fromFloat(Math.pow(base.asFloat(), exp.asFloat()));
}

export function mathPi(): Value {
  return Value.fromFloat(Math.PI);
}

export function mathE(): Value {
  return Value.fromFloat(Math.E);
}

// ============================================================================
// JSON Operations (basic implementation)
// ============================================================================

// Note: Full JSON support would require a JSON library for AssemblyScript
// This is a simplified implementation

export function jsonStringify(v: Value): Value {
  return Value.fromString(valueToJson(v));
}

function valueToJson(v: Value): string {
  switch (v.type) {
    case ValueType.NULL:
      return "null";
    case ValueType.BOOL:
      return v.asBool() ? "true" : "false";
    case ValueType.INT:
      return v.asInt().toString();
    case ValueType.FLOAT:
      return v.asFloat().toString();
    case ValueType.STRING:
      return '"' + escapeJsonString(v.asString()) + '"';
    case ValueType.ARRAY:
    case ValueType.TUPLE:
      const arr = v.type == ValueType.ARRAY ? v.asArray() : v.asTuple();
      const items: string[] = [];
      for (let i = 0; i < arr.length; i++) {
        items.push(valueToJson(arr[i]));
      }
      return "[" + items.join(",") + "]";
    case ValueType.MAP:
    case ValueType.RECORD:
      const m = v.type == ValueType.MAP ? v.asMap() : v.asRecord();
      const keys = m.keys();
      const pairs: string[] = [];
      for (let i = 0; i < keys.length; i++) {
        const k = keys[i];
        const val = m.get(k);
        pairs.push('"' + k.toString() + '":' + valueToJson(val));
      }
      return "{" + pairs.join(",") + "}";
    default:
      return "null";
  }
}

function escapeJsonString(s: string): string {
  let result = "";
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c == 0x22) result += '\\"';       // "
    else if (c == 0x5C) result += "\\\\"; // \
    else if (c == 0x0A) result += "\\n";  // newline
    else if (c == 0x0D) result += "\\r";  // carriage return
    else if (c == 0x09) result += "\\t";  // tab
    else result += String.fromCharCode(c);
  }
  return result;
}

// Note: jsonParse would require a full JSON parser which is complex
// For now, we'll leave it as a stub that throws an error
export function jsonParse(s: Value): Value {
  throw new Error("JSON parsing not yet implemented in WASM runtime");
}

// ============================================================================
// Regex Operations (stubs - require assemblyscript-regex library)
// ============================================================================

export function regexMatch(str: Value, pattern: Value): Value {
  throw new Error("Regex not yet implemented in WASM runtime");
}

export function regexFindAll(str: Value, pattern: Value): Value {
  throw new Error("Regex not yet implemented in WASM runtime");
}

export function regexReplace(str: Value, pattern: Value, replacement: Value): Value {
  throw new Error("Regex not yet implemented in WASM runtime");
}

export function regexSplit(str: Value, pattern: Value): Value {
  throw new Error("Regex not yet implemented in WASM runtime");
}
