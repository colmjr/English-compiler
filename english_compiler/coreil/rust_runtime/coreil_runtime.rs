// Core IL Runtime Library for Rust
//
// This file provides the runtime support for Core IL v1.10 programs compiled to Rust.
// It implements Python-compatible semantics for all operations.
//
// Requirements: Rust stable (no external crates, only std)
// Usage: `include!("coreil_runtime.rs");` from generated code
//
// Version: 1.10

// Note: #![allow(...)] attributes are emitted in the generated program.rs
// (the crate root) since include!() files cannot use inner attributes.

use std::cell::RefCell;
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap, HashSet, VecDeque};
use std::fmt;
use std::rc::Rc;

// ============================================================================
// OrderedMap - Python dict semantics (insertion-order preserving)
// ============================================================================

#[derive(Clone, Debug)]
struct OrderedMap {
    entries: Vec<(Value, Value)>,
    index: HashMap<String, usize>,
}

impl OrderedMap {
    fn new() -> Self {
        OrderedMap {
            entries: Vec::new(),
            index: HashMap::new(),
        }
    }

    fn set(&mut self, key: Value, value: Value) {
        let skey = serialize_value(&key);
        if let Some(&idx) = self.index.get(&skey) {
            self.entries[idx].1 = value;
        } else {
            let idx = self.entries.len();
            self.entries.push((key, value));
            self.index.insert(skey, idx);
        }
    }

    fn get(&self, key: &Value) -> Option<&Value> {
        let skey = serialize_value(key);
        self.index.get(&skey).map(|&idx| &self.entries[idx].1)
    }

    fn get_default(&self, key: &Value, default: &Value) -> Value {
        match self.get(key) {
            Some(v) => v.clone(),
            None => default.clone(),
        }
    }

    fn keys(&self) -> Vec<Value> {
        self.entries.iter().map(|(k, _)| k.clone()).collect()
    }

    fn size(&self) -> usize {
        self.entries.len()
    }

    fn contains_key(&self, key: &Value) -> bool {
        let skey = serialize_value(key);
        self.index.contains_key(&skey)
    }
}

// ============================================================================
// OrderedSet - Python set semantics (insertion-order for determinism)
// ============================================================================

#[derive(Clone, Debug)]
struct OrderedSet {
    items: Vec<Value>,
    index: HashSet<String>,
}

impl OrderedSet {
    fn new() -> Self {
        OrderedSet {
            items: Vec::new(),
            index: HashSet::new(),
        }
    }

    fn add(&mut self, item: Value) {
        let skey = serialize_value(&item);
        if !self.index.contains(&skey) {
            self.index.insert(skey);
            self.items.push(item);
        }
    }

    fn has(&self, item: &Value) -> bool {
        let skey = serialize_value(item);
        self.index.contains(&skey)
    }

    fn remove(&mut self, item: &Value) {
        let skey = serialize_value(item);
        if self.index.remove(&skey) {
            self.items.retain(|v| serialize_value(v) != skey);
            // Rebuild index positions are not needed since we use HashSet
        }
    }

    fn size(&self) -> usize {
        self.items.len()
    }
}

// ============================================================================
// CoreILHeap - Min-heap with stable ordering (insertion order tiebreaker)
// ============================================================================

#[derive(Clone, Debug)]
struct HeapEntry {
    priority: f64,
    counter: u64,
    value: Value,
}

impl PartialEq for HeapEntry {
    fn eq(&self, other: &Self) -> bool {
        self.priority == other.priority && self.counter == other.counter
    }
}

impl Eq for HeapEntry {}

impl PartialOrd for HeapEntry {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for HeapEntry {
    fn cmp(&self, other: &Self) -> Ordering {
        // Reverse ordering for min-heap (BinaryHeap is max-heap by default)
        match other
            .priority
            .partial_cmp(&self.priority)
            .unwrap_or(Ordering::Equal)
        {
            Ordering::Equal => other.counter.cmp(&self.counter),
            ord => ord,
        }
    }
}

#[derive(Clone, Debug)]
struct CoreILHeap {
    heap: BinaryHeap<HeapEntry>,
    counter: u64,
}

impl CoreILHeap {
    fn new() -> Self {
        CoreILHeap {
            heap: BinaryHeap::new(),
            counter: 0,
        }
    }

    fn push(&mut self, priority: f64, value: Value) {
        let entry = HeapEntry {
            priority,
            counter: self.counter,
            value,
        };
        self.counter += 1;
        self.heap.push(entry);
    }

    fn pop(&mut self) -> Value {
        match self.heap.pop() {
            Some(entry) => entry.value,
            None => panic!("pop from empty heap"),
        }
    }

    fn peek(&self) -> Value {
        match self.heap.peek() {
            Some(entry) => entry.value.clone(),
            None => panic!("peek at empty heap"),
        }
    }

    fn size(&self) -> usize {
        self.heap.len()
    }
}

// ============================================================================
// Value - The universal type for Core IL
// ============================================================================

#[derive(Clone, Debug)]
enum Value {
    None,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Array(Rc<RefCell<Vec<Value>>>),
    Tuple(Rc<Vec<Value>>),
    Map(Rc<RefCell<OrderedMap>>),
    Set(Rc<RefCell<OrderedSet>>),
    Record(Rc<RefCell<OrderedMap>>),
    Deque(Rc<RefCell<VecDeque<Value>>>),
    Heap(Rc<RefCell<CoreILHeap>>),
}

// ============================================================================
// Value Serialization (for map/set keys)
// ============================================================================

fn serialize_value(v: &Value) -> String {
    match v {
        Value::None => "N".to_string(),
        Value::Bool(b) => {
            if *b {
                "B1".to_string()
            } else {
                "B0".to_string()
            }
        }
        Value::Int(n) => format!("I{}", n),
        Value::Float(f) => format!("F{:.17}", f),
        Value::Str(s) => format!("S{}:{}", s.len(), s),
        Value::Tuple(items) => {
            let parts: Vec<String> = items.iter().map(|v| serialize_value(v)).collect();
            format!("T({})", parts.join(","))
        }
        Value::Array(arr) => {
            let arr = arr.borrow();
            let parts: Vec<String> = arr.iter().map(|v| serialize_value(v)).collect();
            format!("A[{}]", parts.join(","))
        }
        Value::Map(_) => format!("M@{:p}", Rc::as_ptr(match v { Value::Map(m) => m, _ => unreachable!() })),
        Value::Set(_) => format!("SET@{:p}", Rc::as_ptr(match v { Value::Set(s) => s, _ => unreachable!() })),
        Value::Record(_) => format!("R@{:p}", Rc::as_ptr(match v { Value::Record(r) => r, _ => unreachable!() })),
        Value::Deque(_) => format!("DQ@{:p}", Rc::as_ptr(match v { Value::Deque(d) => d, _ => unreachable!() })),
        Value::Heap(_) => format!("H@{:p}", Rc::as_ptr(match v { Value::Heap(h) => h, _ => unreachable!() })),
    }
}

// ============================================================================
// Python-compatible formatting
// ============================================================================

/// Format a value for display inside a container (strings get single-quoted)
fn format_value_repr(v: &Value) -> String {
    match v {
        Value::Str(s) => format!("'{}'", s),
        _ => format_value(v),
    }
}

/// Format a value for display (top-level print, strings shown raw)
fn format_value(v: &Value) -> String {
    match v {
        Value::None => "None".to_string(),
        Value::Bool(b) => {
            if *b {
                "True".to_string()
            } else {
                "False".to_string()
            }
        }
        Value::Int(n) => format!("{}", n),
        Value::Float(f) => format_float(*f),
        Value::Str(s) => s.clone(),
        Value::Array(arr) => {
            let arr = arr.borrow();
            let parts: Vec<String> = arr.iter().map(|v| format_value_repr(v)).collect();
            format!("[{}]", parts.join(", "))
        }
        Value::Tuple(items) => {
            let parts: Vec<String> = items.iter().map(|v| format_value_repr(v)).collect();
            if items.len() == 1 {
                format!("({},)", parts[0])
            } else {
                format!("({})", parts.join(", "))
            }
        }
        Value::Map(map) => {
            let map = map.borrow();
            let parts: Vec<String> = map
                .entries
                .iter()
                .map(|(k, v)| format!("{}: {}", format_value_repr(k), format_value_repr(v)))
                .collect();
            format!("{{{}}}", parts.join(", "))
        }
        Value::Set(set) => {
            let set = set.borrow();
            if set.items.is_empty() {
                "set()".to_string()
            } else {
                let parts: Vec<String> = set.items.iter().map(|v| format_value_repr(v)).collect();
                format!("{{{}}}", parts.join(", "))
            }
        }
        Value::Record(rec) => {
            let rec = rec.borrow();
            let parts: Vec<String> = rec
                .entries
                .iter()
                .map(|(k, v)| {
                    let key_str = format_value_repr(k);
                    format!("{}: {}", key_str, format_value_repr(v))
                })
                .collect();
            format!("{{{}}}", parts.join(", "))
        }
        Value::Deque(dq) => {
            let dq = dq.borrow();
            let parts: Vec<String> = dq.iter().map(|v| format_value_repr(v)).collect();
            format!("deque([{}])", parts.join(", "))
        }
        Value::Heap(_) => "<heap>".to_string(),
    }
}

/// Format a float value with Python-compatible output
fn format_float(f: f64) -> String {
    if f.is_nan() {
        return "nan".to_string();
    }
    if f.is_infinite() {
        return if f > 0.0 {
            "inf".to_string()
        } else {
            "-inf".to_string()
        };
    }
    // If the float is an integer value, show with .0
    if f == f.floor() && f.abs() < 1e15 {
        format!("{}.0", f as i64)
    } else {
        // Use Python-like repr precision
        // Rust's default Display for f64 generally matches Python well
        let s = format!("{}", f);
        // If it doesn't contain a dot, add .0
        if !s.contains('.') && !s.contains('e') && !s.contains('E') {
            format!("{}.0", s)
        } else {
            s
        }
    }
}

// ============================================================================
// Print
// ============================================================================

fn coreil_print(args: &[Value]) {
    let parts: Vec<String> = args.iter().map(|v| format_value(v)).collect();
    println!("{}", parts.join(" "));
}

// ============================================================================
// Truthiness (Python semantics)
// ============================================================================

fn is_truthy(v: &Value) -> bool {
    match v {
        Value::None => false,
        Value::Bool(b) => *b,
        Value::Int(n) => *n != 0,
        Value::Float(f) => *f != 0.0,
        Value::Str(s) => !s.is_empty(),
        Value::Array(arr) => !arr.borrow().is_empty(),
        Value::Tuple(items) => !items.is_empty(),
        Value::Map(map) => !map.borrow().entries.is_empty(),
        Value::Set(set) => !set.borrow().items.is_empty(),
        Value::Record(_) => true,
        Value::Deque(dq) => !dq.borrow().is_empty(),
        Value::Heap(h) => h.borrow().size() > 0,
    }
}

fn logical_not(v: &Value) -> Value {
    Value::Bool(!is_truthy(v))
}

// ============================================================================
// Type coercion
// ============================================================================

fn as_int(v: &Value) -> i64 {
    match v {
        Value::Int(n) => *n,
        Value::Float(f) => *f as i64,
        Value::Bool(b) => {
            if *b {
                1
            } else {
                0
            }
        }
        Value::Str(s) => s.parse::<i64>().unwrap_or_else(|_| {
            // Try parsing as float then truncating
            s.parse::<f64>()
                .map(|f| f as i64)
                .unwrap_or_else(|_| panic!("cannot convert '{}' to int", s))
        }),
        _ => panic!("cannot convert {:?} to int", type_name(v)),
    }
}

fn as_float(v: &Value) -> f64 {
    match v {
        Value::Int(n) => *n as f64,
        Value::Float(f) => *f,
        Value::Bool(b) => {
            if *b {
                1.0
            } else {
                0.0
            }
        }
        Value::Str(s) => s
            .parse::<f64>()
            .unwrap_or_else(|_| panic!("cannot convert '{}' to float", s)),
        _ => panic!("cannot convert {:?} to float", type_name(v)),
    }
}

fn as_string(v: &Value) -> String {
    format_value(v)
}

fn as_bool(v: &Value) -> bool {
    is_truthy(v)
}

fn to_string_value(v: &Value) -> Value {
    Value::Str(format_value(v))
}

fn type_name(v: &Value) -> &'static str {
    match v {
        Value::None => "None",
        Value::Bool(_) => "bool",
        Value::Int(_) => "int",
        Value::Float(_) => "float",
        Value::Str(_) => "str",
        Value::Array(_) => "list",
        Value::Tuple(_) => "tuple",
        Value::Map(_) => "dict",
        Value::Set(_) => "set",
        Value::Record(_) => "record",
        Value::Deque(_) => "deque",
        Value::Heap(_) => "heap",
    }
}

// ============================================================================
// Numeric helpers
// ============================================================================

/// Extract a numeric value as f64 for arithmetic
fn to_numeric(v: &Value) -> f64 {
    match v {
        Value::Int(n) => *n as f64,
        Value::Float(f) => *f,
        Value::Bool(b) => {
            if *b {
                1.0
            } else {
                0.0
            }
        }
        _ => panic!("expected numeric value, got {}", type_name(v)),
    }
}

/// Check if a value is numeric (int, float, or bool)
fn is_numeric(v: &Value) -> bool {
    matches!(v, Value::Int(_) | Value::Float(_) | Value::Bool(_))
}

/// Return an integer result if both operands are integer-compatible, otherwise float
fn numeric_result(a: &Value, b: &Value, int_op: impl Fn(i64, i64) -> i64, float_op: impl Fn(f64, f64) -> f64) -> Value {
    match (a, b) {
        (Value::Int(x), Value::Int(y)) => Value::Int(int_op(*x, *y)),
        (Value::Bool(x), Value::Int(y)) => Value::Int(int_op(if *x { 1 } else { 0 }, *y)),
        (Value::Int(x), Value::Bool(y)) => Value::Int(int_op(*x, if *y { 1 } else { 0 })),
        (Value::Bool(x), Value::Bool(y)) => {
            Value::Int(int_op(if *x { 1 } else { 0 }, if *y { 1 } else { 0 }))
        }
        _ => Value::Float(float_op(to_numeric(a), to_numeric(b))),
    }
}

// ============================================================================
// Binary Operations
// ============================================================================

fn op_add(a: &Value, b: &Value) -> Value {
    // String concatenation: string + anything or anything + string
    match (a, b) {
        (Value::Str(s1), Value::Str(s2)) => Value::Str(format!("{}{}", s1, s2)),
        (Value::Str(s), other) => Value::Str(format!("{}{}", s, format_value(other))),
        (other, Value::Str(s)) => Value::Str(format!("{}{}", format_value(other), s)),
        // Array concatenation
        (Value::Array(a1), Value::Array(a2)) => {
            let mut result = a1.borrow().clone();
            result.extend(a2.borrow().iter().cloned());
            Value::Array(Rc::new(RefCell::new(result)))
        }
        _ => numeric_result(a, b, |x, y| x + y, |x, y| x + y),
    }
}

fn op_subtract(a: &Value, b: &Value) -> Value {
    numeric_result(a, b, |x, y| x - y, |x, y| x - y)
}

fn op_multiply(a: &Value, b: &Value) -> Value {
    // String repetition
    match (a, b) {
        (Value::Str(s), Value::Int(n)) => {
            if *n <= 0 {
                Value::Str(String::new())
            } else {
                Value::Str(s.repeat(*n as usize))
            }
        }
        (Value::Int(n), Value::Str(s)) => {
            if *n <= 0 {
                Value::Str(String::new())
            } else {
                Value::Str(s.repeat(*n as usize))
            }
        }
        _ => numeric_result(a, b, |x, y| x * y, |x, y| x * y),
    }
}

fn op_divide(a: &Value, b: &Value) -> Value {
    // Division always returns float (Python's /)
    let fa = to_numeric(a);
    let fb = to_numeric(b);
    if fb == 0.0 {
        panic!("division by zero");
    }
    Value::Float(fa / fb)
}

fn op_floor_divide(a: &Value, b: &Value) -> Value {
    // Python's // operator: floor division (rounds towards negative infinity)
    match (a, b) {
        (Value::Int(x), Value::Int(y)) => {
            if *y == 0 {
                panic!("division by zero");
            }
            // Use f64 floor to get Python-compatible floor division
            let result = (*x as f64 / *y as f64).floor() as i64;
            Value::Int(result)
        }
        _ => {
            let fa = to_numeric(a);
            let fb = to_numeric(b);
            if fb == 0.0 {
                panic!("division by zero");
            }
            Value::Float((fa / fb).floor())
        }
    }
}

fn op_modulo(a: &Value, b: &Value) -> Value {
    // Python semantics: result has same sign as divisor
    match (a, b) {
        (Value::Int(x), Value::Int(y)) => {
            if *y == 0 {
                panic!("division by zero");
            }
            Value::Int(x.rem_euclid(*y))
        }
        _ => {
            let fa = to_numeric(a);
            let fb = to_numeric(b);
            if fb == 0.0 {
                panic!("division by zero");
            }
            // Python modulo: result = a - floor(a/b) * b
            let result = fa - (fa / fb).floor() * fb;
            Value::Float(result)
        }
    }
}

fn op_power(a: &Value, b: &Value) -> Value {
    match (a, b) {
        (Value::Int(base), Value::Int(exp)) => {
            if *exp >= 0 {
                Value::Int(base.pow(*exp as u32))
            } else {
                Value::Float((*base as f64).powf(*exp as f64))
            }
        }
        _ => Value::Float(to_numeric(a).powf(to_numeric(b))),
    }
}

// ============================================================================
// Comparison Operations
// ============================================================================

fn op_equal(a: &Value, b: &Value) -> Value {
    Value::Bool(values_equal(a, b))
}

fn values_equal(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::None, Value::None) => true,
        (Value::Bool(x), Value::Bool(y)) => x == y,
        (Value::Int(x), Value::Int(y)) => x == y,
        (Value::Float(x), Value::Float(y)) => x == y,
        (Value::Str(x), Value::Str(y)) => x == y,
        // Cross-type numeric comparison
        (Value::Int(x), Value::Float(y)) => (*x as f64) == *y,
        (Value::Float(x), Value::Int(y)) => *x == (*y as f64),
        (Value::Bool(x), Value::Int(y)) => (if *x { 1i64 } else { 0i64 }) == *y,
        (Value::Int(x), Value::Bool(y)) => *x == (if *y { 1i64 } else { 0i64 }),
        (Value::Bool(x), Value::Float(y)) => (if *x { 1.0 } else { 0.0 }) == *y,
        (Value::Float(x), Value::Bool(y)) => *x == (if *y { 1.0 } else { 0.0 }),
        // Array deep comparison
        (Value::Array(a1), Value::Array(a2)) => {
            let a1 = a1.borrow();
            let a2 = a2.borrow();
            if a1.len() != a2.len() {
                return false;
            }
            a1.iter().zip(a2.iter()).all(|(x, y)| values_equal(x, y))
        }
        // Tuple deep comparison
        (Value::Tuple(t1), Value::Tuple(t2)) => {
            if t1.len() != t2.len() {
                return false;
            }
            t1.iter().zip(t2.iter()).all(|(x, y)| values_equal(x, y))
        }
        // Map deep comparison
        (Value::Map(m1), Value::Map(m2)) => {
            let m1 = m1.borrow();
            let m2 = m2.borrow();
            if m1.entries.len() != m2.entries.len() {
                return false;
            }
            m1.entries
                .iter()
                .zip(m2.entries.iter())
                .all(|((k1, v1), (k2, v2))| values_equal(k1, k2) && values_equal(v1, v2))
        }
        // Set comparison (order-independent)
        (Value::Set(s1), Value::Set(s2)) => {
            let s1 = s1.borrow();
            let s2 = s2.borrow();
            if s1.items.len() != s2.items.len() {
                return false;
            }
            s1.items.iter().all(|item| s2.has(item))
        }
        _ => false,
    }
}

fn op_not_equal(a: &Value, b: &Value) -> Value {
    Value::Bool(!values_equal(a, b))
}

fn compare_values(a: &Value, b: &Value) -> Ordering {
    match (a, b) {
        // Numeric comparisons
        (Value::Int(x), Value::Int(y)) => x.cmp(y),
        (Value::Float(x), Value::Float(y)) => x.partial_cmp(y).unwrap_or(Ordering::Equal),
        (Value::Int(x), Value::Float(y)) => (*x as f64)
            .partial_cmp(y)
            .unwrap_or(Ordering::Equal),
        (Value::Float(x), Value::Int(y)) => x
            .partial_cmp(&(*y as f64))
            .unwrap_or(Ordering::Equal),
        (Value::Bool(x), other) if is_numeric(other) => {
            let xn = if *x { 1i64 } else { 0 };
            compare_values(&Value::Int(xn), other)
        }
        (other, Value::Bool(y)) if is_numeric(other) => {
            let yn = if *y { 1i64 } else { 0 };
            compare_values(other, &Value::Int(yn))
        }
        (Value::Bool(x), Value::Bool(y)) => {
            let xi: i64 = if *x { 1 } else { 0 };
            let yi: i64 = if *y { 1 } else { 0 };
            xi.cmp(&yi)
        }
        // String comparison
        (Value::Str(x), Value::Str(y)) => x.cmp(y),
        _ => panic!(
            "cannot compare {} and {}",
            type_name(a),
            type_name(b)
        ),
    }
}

fn op_less_than(a: &Value, b: &Value) -> Value {
    Value::Bool(compare_values(a, b) == Ordering::Less)
}

fn op_less_than_or_equal(a: &Value, b: &Value) -> Value {
    Value::Bool(compare_values(a, b) != Ordering::Greater)
}

fn op_greater_than(a: &Value, b: &Value) -> Value {
    Value::Bool(compare_values(a, b) == Ordering::Greater)
}

fn op_greater_than_or_equal(a: &Value, b: &Value) -> Value {
    Value::Bool(compare_values(a, b) != Ordering::Less)
}

// ============================================================================
// Array Operations
// ============================================================================

fn make_array(items: Vec<Value>) -> Value {
    Value::Array(Rc::new(RefCell::new(items)))
}

/// Resolve a Python-style index (supports negative indexing)
fn resolve_index(idx: i64, len: usize) -> usize {
    let resolved = if idx < 0 { len as i64 + idx } else { idx };
    if resolved < 0 || resolved >= len as i64 {
        panic!(
            "index {} out of range for length {}",
            idx, len
        );
    }
    resolved as usize
}

fn array_index(arr: &Value, index: &Value) -> Value {
    match arr {
        Value::Array(a) => {
            let a = a.borrow();
            let idx = as_int(index);
            let resolved = resolve_index(idx, a.len());
            a[resolved].clone()
        }
        Value::Str(s) => {
            let idx = as_int(index);
            let chars: Vec<char> = s.chars().collect();
            let resolved = resolve_index(idx, chars.len());
            Value::Str(chars[resolved].to_string())
        }
        Value::Tuple(items) => {
            let idx = as_int(index);
            let resolved = resolve_index(idx, items.len());
            items[resolved].clone()
        }
        _ => panic!("cannot index into {}", type_name(arr)),
    }
}

fn array_set_index(arr: &Value, index: &Value, value: Value) {
    match arr {
        Value::Array(a) => {
            let mut a = a.borrow_mut();
            let idx = as_int(index);
            let resolved = resolve_index(idx, a.len());
            a[resolved] = value;
        }
        _ => panic!("cannot set index on {}", type_name(arr)),
    }
}

fn array_push(arr: &Value, value: Value) {
    match arr {
        Value::Array(a) => {
            a.borrow_mut().push(value);
        }
        _ => panic!("cannot push to {}", type_name(arr)),
    }
}

fn array_length(v: &Value) -> Value {
    match v {
        Value::Array(a) => Value::Int(a.borrow().len() as i64),
        Value::Str(s) => Value::Int(s.chars().count() as i64),
        Value::Tuple(items) => Value::Int(items.len() as i64),
        Value::Map(m) => Value::Int(m.borrow().size() as i64),
        _ => panic!("cannot get length of {}", type_name(v)),
    }
}

fn array_slice(arr: &Value, start: &Value, end: &Value) -> Value {
    match arr {
        Value::Array(a) => {
            let a = a.borrow();
            let len = a.len() as i64;
            let s = resolve_slice_index(as_int(start), len);
            let e = resolve_slice_index(as_int(end), len);
            if s >= e {
                make_array(vec![])
            } else {
                make_array(a[s..e].to_vec())
            }
        }
        Value::Str(st) => {
            let chars: Vec<char> = st.chars().collect();
            let len = chars.len() as i64;
            let s = resolve_slice_index(as_int(start), len);
            let e = resolve_slice_index(as_int(end), len);
            if s >= e {
                Value::Str(String::new())
            } else {
                Value::Str(chars[s..e].iter().collect())
            }
        }
        _ => panic!("cannot slice {}", type_name(arr)),
    }
}

/// Resolve slice index (clamps rather than panicking, supports negative)
fn resolve_slice_index(idx: i64, len: i64) -> usize {
    let resolved = if idx < 0 { len + idx } else { idx };
    // Clamp to valid range
    if resolved < 0 {
        0
    } else if resolved > len {
        len as usize
    } else {
        resolved as usize
    }
}

// ============================================================================
// Tuple Operations
// ============================================================================

fn make_tuple(items: Vec<Value>) -> Value {
    Value::Tuple(Rc::new(items))
}

// ============================================================================
// Map Operations
// ============================================================================

fn make_map(pairs: Vec<(Value, Value)>) -> Value {
    let mut map = OrderedMap::new();
    for (k, v) in pairs {
        map.set(k, v);
    }
    Value::Map(Rc::new(RefCell::new(map)))
}

fn map_set(map: &Value, key: Value, value: Value) {
    match map {
        Value::Map(m) => {
            m.borrow_mut().set(key, value);
        }
        _ => panic!("cannot set on {}", type_name(map)),
    }
}

fn map_get(map: &Value, key: &Value) -> Value {
    match map {
        Value::Map(m) => {
            let m = m.borrow();
            match m.get(key) {
                Some(v) => v.clone(),
                None => panic!("key not found: {}", format_value(key)),
            }
        }
        _ => panic!("cannot get from {}", type_name(map)),
    }
}

fn map_get_default(map: &Value, key: &Value, default: &Value) -> Value {
    match map {
        Value::Map(m) => m.borrow().get_default(key, default),
        _ => panic!("cannot get_default from {}", type_name(map)),
    }
}

fn map_keys(map: &Value) -> Value {
    match map {
        Value::Map(m) => make_array(m.borrow().keys()),
        _ => panic!("cannot get keys of {}", type_name(map)),
    }
}

fn map_contains(map: &Value, key: &Value) -> Value {
    match map {
        Value::Map(m) => Value::Bool(m.borrow().contains_key(key)),
        _ => panic!("cannot check contains on {}", type_name(map)),
    }
}

// ============================================================================
// Record Operations
// ============================================================================

fn make_record(fields: Vec<(&str, Value)>) -> Value {
    let mut map = OrderedMap::new();
    for (name, value) in fields {
        map.set(Value::Str(name.to_string()), value);
    }
    Value::Record(Rc::new(RefCell::new(map)))
}

fn get_field(record: &Value, field: &str) -> Value {
    match record {
        Value::Record(r) => {
            let r = r.borrow();
            let key = Value::Str(field.to_string());
            match r.get(&key) {
                Some(v) => v.clone(),
                None => panic!("record has no field '{}'", field),
            }
        }
        _ => panic!("cannot get field of {}", type_name(record)),
    }
}

fn set_field(record: &Value, field: &str, value: Value) {
    match record {
        Value::Record(r) => {
            r.borrow_mut()
                .set(Value::Str(field.to_string()), value);
        }
        _ => panic!("cannot set field on {}", type_name(record)),
    }
}

// ============================================================================
// Set Operations
// ============================================================================

fn make_set(items: Vec<Value>) -> Value {
    let mut set = OrderedSet::new();
    for item in items {
        set.add(item);
    }
    Value::Set(Rc::new(RefCell::new(set)))
}

fn set_has(set: &Value, item: &Value) -> Value {
    match set {
        Value::Set(s) => Value::Bool(s.borrow().has(item)),
        _ => panic!("cannot check membership on {}", type_name(set)),
    }
}

fn set_add(set: &Value, item: Value) {
    match set {
        Value::Set(s) => {
            s.borrow_mut().add(item);
        }
        _ => panic!("cannot add to {}", type_name(set)),
    }
}

fn set_remove(set: &Value, item: &Value) {
    match set {
        Value::Set(s) => {
            s.borrow_mut().remove(item);
        }
        _ => panic!("cannot remove from {}", type_name(set)),
    }
}

fn set_size(set: &Value) -> Value {
    match set {
        Value::Set(s) => Value::Int(s.borrow().size() as i64),
        _ => panic!("cannot get size of {}", type_name(set)),
    }
}

// ============================================================================
// Deque Operations
// ============================================================================

fn deque_new() -> Value {
    Value::Deque(Rc::new(RefCell::new(VecDeque::new())))
}

fn deque_push_back(dq: &Value, value: Value) {
    match dq {
        Value::Deque(d) => {
            d.borrow_mut().push_back(value);
        }
        _ => panic!("cannot push_back on {}", type_name(dq)),
    }
}

fn deque_push_front(dq: &Value, value: Value) {
    match dq {
        Value::Deque(d) => {
            d.borrow_mut().push_front(value);
        }
        _ => panic!("cannot push_front on {}", type_name(dq)),
    }
}

fn deque_pop_front(dq: &Value) -> Value {
    match dq {
        Value::Deque(d) => d
            .borrow_mut()
            .pop_front()
            .unwrap_or_else(|| panic!("pop from empty deque")),
        _ => panic!("cannot pop_front on {}", type_name(dq)),
    }
}

fn deque_pop_back(dq: &Value) -> Value {
    match dq {
        Value::Deque(d) => d
            .borrow_mut()
            .pop_back()
            .unwrap_or_else(|| panic!("pop from empty deque")),
        _ => panic!("cannot pop_back on {}", type_name(dq)),
    }
}

fn deque_size(dq: &Value) -> Value {
    match dq {
        Value::Deque(d) => Value::Int(d.borrow().len() as i64),
        _ => panic!("cannot get size of {}", type_name(dq)),
    }
}

// ============================================================================
// Heap Operations
// ============================================================================

fn heap_new() -> Value {
    Value::Heap(Rc::new(RefCell::new(CoreILHeap::new())))
}

fn heap_push(heap: &Value, priority: &Value, value: Value) {
    match heap {
        Value::Heap(h) => {
            let p = to_numeric(priority);
            h.borrow_mut().push(p, value);
        }
        _ => panic!("cannot push to {}", type_name(heap)),
    }
}

fn heap_pop(heap: &Value) -> Value {
    match heap {
        Value::Heap(h) => h.borrow_mut().pop(),
        _ => panic!("cannot pop from {}", type_name(heap)),
    }
}

fn heap_peek(heap: &Value) -> Value {
    match heap {
        Value::Heap(h) => h.borrow().peek(),
        _ => panic!("cannot peek at {}", type_name(heap)),
    }
}

fn heap_size(heap: &Value) -> Value {
    match heap {
        Value::Heap(h) => Value::Int(h.borrow().size() as i64),
        _ => panic!("cannot get size of {}", type_name(heap)),
    }
}

// ============================================================================
// String Operations
// ============================================================================

fn string_length(s: &Value) -> Value {
    match s {
        Value::Str(st) => Value::Int(st.chars().count() as i64),
        _ => panic!("string_length requires a string, got {}", type_name(s)),
    }
}

fn string_substring(s: &Value, start: &Value, end: &Value) -> Value {
    match s {
        Value::Str(st) => {
            let chars: Vec<char> = st.chars().collect();
            let len = chars.len() as i64;
            let s_idx = resolve_slice_index(as_int(start), len);
            let e_idx = resolve_slice_index(as_int(end), len);
            if s_idx >= e_idx {
                Value::Str(String::new())
            } else {
                Value::Str(chars[s_idx..e_idx].iter().collect())
            }
        }
        _ => panic!("string_substring requires a string, got {}", type_name(s)),
    }
}

fn string_char_at(s: &Value, index: &Value) -> Value {
    match s {
        Value::Str(st) => {
            let chars: Vec<char> = st.chars().collect();
            let idx = as_int(index);
            let resolved = resolve_index(idx, chars.len());
            Value::Str(chars[resolved].to_string())
        }
        _ => panic!("string_char_at requires a string, got {}", type_name(s)),
    }
}

fn string_join(separator: &Value, arr: &Value) -> Value {
    let sep = match separator {
        Value::Str(s) => s.clone(),
        _ => panic!("join separator must be a string"),
    };
    match arr {
        Value::Array(a) => {
            let a = a.borrow();
            let parts: Vec<String> = a.iter().map(|v| format_value(v)).collect();
            Value::Str(parts.join(&sep))
        }
        _ => panic!("join requires an array, got {}", type_name(arr)),
    }
}

fn string_split(s: &Value, delimiter: &Value) -> Value {
    match (s, delimiter) {
        (Value::Str(st), Value::Str(delim)) => {
            let parts: Vec<Value> = st.split(delim.as_str()).map(|p| Value::Str(p.to_string())).collect();
            make_array(parts)
        }
        _ => panic!("string_split requires string arguments"),
    }
}

fn string_trim(s: &Value) -> Value {
    match s {
        Value::Str(st) => Value::Str(st.trim().to_string()),
        _ => panic!("string_trim requires a string, got {}", type_name(s)),
    }
}

fn string_upper(s: &Value) -> Value {
    match s {
        Value::Str(st) => Value::Str(st.to_uppercase()),
        _ => panic!("string_upper requires a string, got {}", type_name(s)),
    }
}

fn string_lower(s: &Value) -> Value {
    match s {
        Value::Str(st) => Value::Str(st.to_lowercase()),
        _ => panic!("string_lower requires a string, got {}", type_name(s)),
    }
}

fn string_starts_with(s: &Value, prefix: &Value) -> Value {
    match (s, prefix) {
        (Value::Str(st), Value::Str(p)) => Value::Bool(st.starts_with(p.as_str())),
        _ => panic!("string_starts_with requires string arguments"),
    }
}

fn string_ends_with(s: &Value, suffix: &Value) -> Value {
    match (s, suffix) {
        (Value::Str(st), Value::Str(suf)) => Value::Bool(st.ends_with(suf.as_str())),
        _ => panic!("string_ends_with requires string arguments"),
    }
}

fn string_contains(s: &Value, substring: &Value) -> Value {
    match (s, substring) {
        (Value::Str(st), Value::Str(sub)) => Value::Bool(st.contains(sub.as_str())),
        _ => panic!("string_contains requires string arguments"),
    }
}

fn string_replace(s: &Value, old: &Value, new_str: &Value) -> Value {
    match (s, old, new_str) {
        (Value::Str(st), Value::Str(o), Value::Str(n)) => {
            Value::Str(st.replace(o.as_str(), n.as_str()))
        }
        _ => panic!("string_replace requires string arguments"),
    }
}

// ============================================================================
// Math Operations
// ============================================================================

fn math_sin(v: &Value) -> Value {
    Value::Float(to_numeric(v).sin())
}

fn math_cos(v: &Value) -> Value {
    Value::Float(to_numeric(v).cos())
}

fn math_tan(v: &Value) -> Value {
    Value::Float(to_numeric(v).tan())
}

fn math_sqrt(v: &Value) -> Value {
    Value::Float(to_numeric(v).sqrt())
}

fn math_floor(v: &Value) -> Value {
    Value::Int(to_numeric(v).floor() as i64)
}

fn math_ceil(v: &Value) -> Value {
    Value::Int(to_numeric(v).ceil() as i64)
}

fn math_abs(v: &Value) -> Value {
    match v {
        Value::Int(n) => Value::Int(n.abs()),
        Value::Float(f) => Value::Float(f.abs()),
        _ => Value::Float(to_numeric(v).abs()),
    }
}

fn math_log(v: &Value) -> Value {
    Value::Float(to_numeric(v).ln())
}

fn math_exp(v: &Value) -> Value {
    Value::Float(to_numeric(v).exp())
}

fn math_pow(base: &Value, exponent: &Value) -> Value {
    op_power(base, exponent)
}

fn math_pi() -> Value {
    Value::Float(std::f64::consts::PI)
}

fn math_e() -> Value {
    Value::Float(std::f64::consts::E)
}

// ============================================================================
// JSON Operations — Pure Rust recursive descent parser and serializer
// ============================================================================

#[derive(Clone, Debug, PartialEq)]
enum JsonToken {
    LBrace, RBrace, LBracket, RBracket, Colon, Comma,
    StringVal(String),
    NumberVal(String),
    True, False, Null,
}

struct JsonLexer { chars: Vec<char>, pos: usize }

impl JsonLexer {
    fn new(input: &str) -> Self { JsonLexer { chars: input.chars().collect(), pos: 0 } }

    fn skip_ws(&mut self) {
        while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_whitespace() { self.pos += 1; }
    }

    fn next_token(&mut self) -> Option<JsonToken> {
        self.skip_ws();
        if self.pos >= self.chars.len() { return None; }
        let ch = self.chars[self.pos];
        match ch {
            '{' => { self.pos += 1; Some(JsonToken::LBrace) }
            '}' => { self.pos += 1; Some(JsonToken::RBrace) }
            '[' => { self.pos += 1; Some(JsonToken::LBracket) }
            ']' => { self.pos += 1; Some(JsonToken::RBracket) }
            ':' => { self.pos += 1; Some(JsonToken::Colon) }
            ',' => { self.pos += 1; Some(JsonToken::Comma) }
            '"' => Some(self.lex_string()),
            't' => self.lex_kw("true", JsonToken::True),
            'f' => self.lex_kw("false", JsonToken::False),
            'n' => self.lex_kw("null", JsonToken::Null),
            '-' | '0'..='9' => Some(self.lex_number()),
            _ => panic!("runtime error: invalid JSON: unexpected '{}'", ch),
        }
    }

    fn lex_string(&mut self) -> JsonToken {
        self.pos += 1;
        let mut s = String::new();
        while self.pos < self.chars.len() {
            let ch = self.chars[self.pos];
            if ch == '"' { self.pos += 1; return JsonToken::StringVal(s); }
            if ch == '\\' {
                self.pos += 1;
                if self.pos >= self.chars.len() { panic!("runtime error: invalid JSON: unterminated escape"); }
                match self.chars[self.pos] {
                    '"' => s.push('"'), '\\' => s.push('\\'), '/' => s.push('/'),
                    'b' => s.push('\u{08}'), 'f' => s.push('\u{0C}'),
                    'n' => s.push('\n'), 'r' => s.push('\r'), 't' => s.push('\t'),
                    'u' => {
                        let mut hex = String::new();
                        for _ in 0..4 { self.pos += 1; hex.push(self.chars[self.pos]); }
                        if let Some(c) = char::from_u32(u32::from_str_radix(&hex, 16).unwrap_or(0)) { s.push(c); }
                    }
                    c => s.push(c),
                }
            } else { s.push(ch); }
            self.pos += 1;
        }
        panic!("runtime error: invalid JSON: unterminated string");
    }

    fn lex_number(&mut self) -> JsonToken {
        let start = self.pos;
        if self.chars[self.pos] == '-' { self.pos += 1; }
        while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_digit() { self.pos += 1; }
        if self.pos < self.chars.len() && self.chars[self.pos] == '.' {
            self.pos += 1;
            while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_digit() { self.pos += 1; }
        }
        if self.pos < self.chars.len() && (self.chars[self.pos] == 'e' || self.chars[self.pos] == 'E') {
            self.pos += 1;
            if self.pos < self.chars.len() && (self.chars[self.pos] == '+' || self.chars[self.pos] == '-') { self.pos += 1; }
            while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_digit() { self.pos += 1; }
        }
        JsonToken::NumberVal(self.chars[start..self.pos].iter().collect())
    }

    fn lex_kw(&mut self, kw: &str, tok: JsonToken) -> Option<JsonToken> {
        let kc: Vec<char> = kw.chars().collect();
        for (i, &c) in kc.iter().enumerate() {
            if self.pos + i >= self.chars.len() || self.chars[self.pos + i] != c {
                panic!("runtime error: invalid JSON: unexpected token");
            }
        }
        self.pos += kc.len();
        Some(tok)
    }
}

struct JsonParser { tokens: Vec<JsonToken>, pos: usize }

impl JsonParser {
    fn new(input: &str) -> Self {
        let mut lex = JsonLexer::new(input);
        let mut tokens = Vec::new();
        while let Some(t) = lex.next_token() { tokens.push(t); }
        JsonParser { tokens, pos: 0 }
    }
    fn peek(&self) -> Option<&JsonToken> { self.tokens.get(self.pos) }
    fn next(&mut self) -> JsonToken {
        let t = self.tokens.get(self.pos).cloned().unwrap_or_else(|| panic!("runtime error: invalid JSON: unexpected end"));
        self.pos += 1; t
    }
    fn expect(&mut self, e: &JsonToken) { let t = self.next(); if &t != e { panic!("runtime error: invalid JSON: expected {:?}", e); } }

    fn parse_value(&mut self) -> Value {
        match self.peek().cloned() {
            Some(JsonToken::LBrace) => self.parse_object(),
            Some(JsonToken::LBracket) => self.parse_array(),
            Some(JsonToken::StringVal(_)) => { if let JsonToken::StringVal(s) = self.next() { Value::Str(s) } else { unreachable!() } }
            Some(JsonToken::NumberVal(_)) => {
                if let JsonToken::NumberVal(s) = self.next() {
                    if s.contains('.') || s.contains('e') || s.contains('E') {
                        Value::Float(s.parse().unwrap_or_else(|_| panic!("runtime error: invalid JSON number")))
                    } else {
                        Value::Int(s.parse().unwrap_or_else(|_| panic!("runtime error: invalid JSON number")))
                    }
                } else { unreachable!() }
            }
            Some(JsonToken::True) => { self.next(); Value::Bool(true) }
            Some(JsonToken::False) => { self.next(); Value::Bool(false) }
            Some(JsonToken::Null) => { self.next(); Value::None }
            _ => panic!("runtime error: invalid JSON: unexpected token"),
        }
    }

    fn parse_object(&mut self) -> Value {
        self.expect(&JsonToken::LBrace);
        let mut map = OrderedMap::new();
        if self.peek() == Some(&JsonToken::RBrace) { self.next(); return Value::Map(Rc::new(RefCell::new(map))); }
        loop {
            let key = match self.next() { JsonToken::StringVal(s) => s, _ => panic!("runtime error: invalid JSON: expected string key") };
            self.expect(&JsonToken::Colon);
            let val = self.parse_value();
            map.set(Value::Str(key), val);
            match self.peek() {
                Some(JsonToken::Comma) => { self.next(); }
                Some(JsonToken::RBrace) => { self.next(); break; }
                _ => panic!("runtime error: invalid JSON: expected ',' or '}}'"),
            }
        }
        Value::Map(Rc::new(RefCell::new(map)))
    }

    fn parse_array(&mut self) -> Value {
        self.expect(&JsonToken::LBracket);
        let mut items = Vec::new();
        if self.peek() == Some(&JsonToken::RBracket) { self.next(); return make_array(items); }
        loop {
            items.push(self.parse_value());
            match self.peek() {
                Some(JsonToken::Comma) => { self.next(); }
                Some(JsonToken::RBracket) => { self.next(); break; }
                _ => panic!("runtime error: invalid JSON: expected ',' or ']'"),
            }
        }
        make_array(items)
    }
}

fn json_parse_val(s: &Value) -> Value {
    let input = match s { Value::Str(st) => st.clone(), _ => panic!("runtime error: JsonParse source must be a string") };
    let mut parser = JsonParser::new(&input);
    parser.parse_value()
}

fn json_serialize(v: &Value, indent: Option<usize>, depth: usize) -> String {
    match v {
        Value::None => "null".to_string(),
        Value::Bool(b) => if *b { "true".to_string() } else { "false".to_string() },
        Value::Int(n) => format!("{}", n),
        Value::Float(f) => {
            if *f == f.floor() && f.abs() < 1e15 { format!("{}.0", *f as i64) } else { format!("{}", f) }
        }
        Value::Str(s) => {
            let mut r = String::from('"');
            for ch in s.chars() {
                match ch {
                    '"' => r.push_str("\\\""), '\\' => r.push_str("\\\\"),
                    '\n' => r.push_str("\\n"), '\r' => r.push_str("\\r"), '\t' => r.push_str("\\t"),
                    c if (c as u32) < 0x20 => r.push_str(&format!("\\u{:04x}", c as u32)),
                    c => r.push(c),
                }
            }
            r.push('"'); r
        }
        Value::Array(arr) => {
            let arr = arr.borrow();
            if arr.is_empty() { return "[]".to_string(); }
            match indent {
                Some(ind) => {
                    let inner = " ".repeat(ind * (depth + 1));
                    let outer = " ".repeat(ind * depth);
                    let parts: Vec<String> = arr.iter().map(|i| format!("{}{}", inner, json_serialize(i, Some(ind), depth + 1))).collect();
                    format!("[\n{}\n{}]", parts.join(",\n"), outer)
                }
                None => {
                    let parts: Vec<String> = arr.iter().map(|i| json_serialize(i, None, depth)).collect();
                    format!("[{}]", parts.join(", "))
                }
            }
        }
        Value::Map(map) => {
            let map = map.borrow();
            if map.entries.is_empty() { return "{}".to_string(); }
            match indent {
                Some(ind) => {
                    let inner = " ".repeat(ind * (depth + 1));
                    let outer = " ".repeat(ind * depth);
                    let parts: Vec<String> = map.entries.iter().map(|(k, v)| {
                        format!("{}{}: {}", inner, json_serialize(k, Some(ind), depth + 1), json_serialize(v, Some(ind), depth + 1))
                    }).collect();
                    format!("{{\n{}\n{}}}", parts.join(",\n"), outer)
                }
                None => {
                    let parts: Vec<String> = map.entries.iter().map(|(k, v)| {
                        format!("{}: {}", json_serialize(k, None, depth), json_serialize(v, None, depth))
                    }).collect();
                    format!("{{{}}}", parts.join(", "))
                }
            }
        }
        _ => json_serialize(&Value::Str(format_value(v)), indent, depth),
    }
}

fn json_stringify_val(v: &Value, pretty: &Value) -> Value {
    let indent = if is_truthy(pretty) { Some(2) } else { None };
    Value::Str(json_serialize(v, indent, 0))
}

// ============================================================================
// Regex Operations — Pure Rust NFA-based regex engine
// ============================================================================

#[derive(Clone, Debug)]
enum RxInst {
    Lit(char),
    LitCI(char, char),
    Dot,
    AnchorStart,
    AnchorEnd,
    Class(Vec<(char, char)>, bool),
    Split(usize, usize),
    Jump(usize),
    Match,
}

fn rx_compile(pattern: &str, ci: bool) -> Vec<RxInst> {
    let chars: Vec<char> = pattern.chars().collect();
    let mut insts = Vec::new();
    rx_compile_inner(&chars, &mut 0, &mut insts, ci, false);
    insts.push(RxInst::Match);
    insts
}

fn rx_compile_inner(chars: &[char], pos: &mut usize, insts: &mut Vec<RxInst>, ci: bool, in_group: bool) {
    let mut alts: Vec<Vec<RxInst>> = vec![Vec::new()];

    while *pos < chars.len() {
        let ch = chars[*pos];
        match ch {
            ')' if in_group => break,
            '|' => { *pos += 1; alts.push(Vec::new()); }
            '(' => {
                *pos += 1;
                let mut sub = Vec::new();
                rx_compile_inner(chars, pos, &mut sub, ci, true);
                if *pos < chars.len() && chars[*pos] == ')' { *pos += 1; }
                rx_apply_quant(chars, pos, &mut sub, alts.last_mut().unwrap());
            }
            '[' => {
                *pos += 1;
                let (ranges, neg) = rx_parse_class(chars, pos);
                let mut sub = vec![RxInst::Class(ranges, neg)];
                rx_apply_quant(chars, pos, &mut sub, alts.last_mut().unwrap());
            }
            '.' => { *pos += 1; let mut sub = vec![RxInst::Dot]; rx_apply_quant(chars, pos, &mut sub, alts.last_mut().unwrap()); }
            '^' => { *pos += 1; alts.last_mut().unwrap().push(RxInst::AnchorStart); }
            '$' => { *pos += 1; alts.last_mut().unwrap().push(RxInst::AnchorEnd); }
            '\\' => {
                *pos += 1;
                if *pos >= chars.len() { panic!("runtime error: invalid regex: trailing backslash"); }
                let esc = chars[*pos]; *pos += 1;
                let mut sub = match esc {
                    'd' => vec![RxInst::Class(vec![('0', '9')], false)],
                    'D' => vec![RxInst::Class(vec![('0', '9')], true)],
                    'w' => vec![RxInst::Class(vec![('a', 'z'), ('A', 'Z'), ('0', '9'), ('_', '_')], false)],
                    'W' => vec![RxInst::Class(vec![('a', 'z'), ('A', 'Z'), ('0', '9'), ('_', '_')], true)],
                    's' => vec![RxInst::Class(vec![(' ', ' '), ('\t', '\t'), ('\n', '\n'), ('\r', '\r')], false)],
                    'S' => vec![RxInst::Class(vec![(' ', ' '), ('\t', '\t'), ('\n', '\n'), ('\r', '\r')], true)],
                    c => if ci && c.is_alphabetic() {
                        vec![RxInst::LitCI(c.to_lowercase().next().unwrap(), c.to_uppercase().next().unwrap())]
                    } else { vec![RxInst::Lit(c)] },
                };
                rx_apply_quant(chars, pos, &mut sub, alts.last_mut().unwrap());
            }
            _ => {
                *pos += 1;
                let mut sub = if ci && ch.is_alphabetic() {
                    vec![RxInst::LitCI(ch.to_lowercase().next().unwrap(), ch.to_uppercase().next().unwrap())]
                } else { vec![RxInst::Lit(ch)] };
                rx_apply_quant(chars, pos, &mut sub, alts.last_mut().unwrap());
            }
        }
    }

    if alts.len() == 1 {
        insts.extend(alts.into_iter().next().unwrap());
    } else {
        rx_build_alt(&alts, 0, insts);
    }
}

fn rx_build_alt(branches: &[Vec<RxInst>], idx: usize, out: &mut Vec<RxInst>) {
    if idx == branches.len() - 1 { out.extend(branches[idx].iter().cloned()); return; }
    let mut remaining = Vec::new();
    rx_build_alt(branches, idx + 1, &mut remaining);
    let blen = branches[idx].len();
    let right = 1 + blen + 1;
    out.push(RxInst::Split(1, right));
    out.extend(branches[idx].iter().cloned());
    out.push(RxInst::Jump(right + remaining.len()));
    out.extend(remaining);
}

fn rx_apply_quant(chars: &[char], pos: &mut usize, sub: &mut Vec<RxInst>, target: &mut Vec<RxInst>) {
    if *pos < chars.len() {
        match chars[*pos] {
            '*' => {
                *pos += 1;
                let greedy = !(*pos < chars.len() && chars[*pos] == '?');
                if !greedy { *pos += 1; }
                let blen = sub.len();
                if greedy { target.push(RxInst::Split(1, blen + 2)); }
                else { target.push(RxInst::Split(blen + 2, 1)); }
                target.extend(sub.drain(..));
                let jt = target.len() - blen - 1;
                target.push(RxInst::Jump(jt));
                return;
            }
            '+' => {
                *pos += 1;
                let greedy = !(*pos < chars.len() && chars[*pos] == '?');
                if !greedy { *pos += 1; }
                let start = target.len();
                target.extend(sub.drain(..));
                if greedy { target.push(RxInst::Split(start, target.len() + 1)); }
                else { target.push(RxInst::Split(target.len() + 1, start)); }
                return;
            }
            '?' => {
                *pos += 1;
                let greedy = !(*pos < chars.len() && chars[*pos] == '?');
                if !greedy { *pos += 1; }
                let spos = target.len();
                target.push(RxInst::Split(0, 0)); // placeholder
                let bstart = target.len();
                target.extend(sub.drain(..));
                let after = target.len();
                if greedy { target[spos] = RxInst::Split(bstart, after); }
                else { target[spos] = RxInst::Split(after, bstart); }
                return;
            }
            _ => {}
        }
    }
    target.extend(sub.drain(..));
}

fn rx_parse_class(chars: &[char], pos: &mut usize) -> (Vec<(char, char)>, bool) {
    let mut ranges = Vec::new();
    let neg = *pos < chars.len() && chars[*pos] == '^';
    if neg { *pos += 1; }
    while *pos < chars.len() && chars[*pos] != ']' {
        let ch = chars[*pos]; *pos += 1;
        let start = if ch == '\\' && *pos < chars.len() {
            let esc = chars[*pos]; *pos += 1;
            match esc {
                'd' => { ranges.push(('0', '9')); continue; }
                'w' => { ranges.extend_from_slice(&[('a','z'),('A','Z'),('0','9'),('_','_')]); continue; }
                's' => { ranges.extend_from_slice(&[(' ',' '),('\t','\t'),('\n','\n'),('\r','\r')]); continue; }
                _ => esc,
            }
        } else { ch };
        if *pos + 1 < chars.len() && chars[*pos] == '-' && chars[*pos + 1] != ']' {
            *pos += 1;
            let end = chars[*pos]; *pos += 1;
            ranges.push((start, end));
        } else {
            ranges.push((start, start));
        }
    }
    if *pos < chars.len() && chars[*pos] == ']' { *pos += 1; }
    (ranges, neg)
}

fn rx_match_at(insts: &[RxInst], input: &[char], start: usize, ci: bool) -> Option<usize> {
    let mut cur: Vec<usize> = Vec::new();
    let mut nxt: Vec<usize> = Vec::new();
    let mut best: Option<usize> = None;

    rx_add_thread(&mut cur, insts, 0, input, start);

    let mut p = start;
    loop {
        if cur.is_empty() { break; }
        // Collect deferred additions for AnchorEnd (cannot mutate cur while iterating)
        let mut anchor_end_adds: Vec<usize> = Vec::new();
        for &pc in &cur {
            if pc >= insts.len() { continue; }
            match &insts[pc] {
                RxInst::Match => { if best.is_none() || p > best.unwrap() { best = Some(p); } }
                RxInst::Lit(ch) => { if p < input.len() && input[p] == *ch { rx_add_thread(&mut nxt, insts, pc + 1, input, p + 1); } }
                RxInst::LitCI(lo, hi) => { if p < input.len() && (input[p] == *lo || input[p] == *hi) { rx_add_thread(&mut nxt, insts, pc + 1, input, p + 1); } }
                RxInst::Dot => { if p < input.len() && input[p] != '\n' { rx_add_thread(&mut nxt, insts, pc + 1, input, p + 1); } }
                RxInst::Class(ranges, neg) => {
                    if p < input.len() {
                        let c = if ci { input[p].to_lowercase().next().unwrap_or(input[p]) } else { input[p] };
                        let mut in_class = false;
                        for &(lo, hi) in ranges {
                            let (lo, hi) = if ci { (lo.to_lowercase().next().unwrap_or(lo), hi.to_lowercase().next().unwrap_or(hi)) } else { (lo, hi) };
                            if c >= lo && c <= hi { in_class = true; break; }
                        }
                        if in_class != *neg { rx_add_thread(&mut nxt, insts, pc + 1, input, p + 1); }
                    }
                }
                RxInst::AnchorEnd => { if p == input.len() { anchor_end_adds.push(pc + 1); } }
                _ => {}
            }
        }
        // Apply deferred AnchorEnd thread additions
        for add_pc in anchor_end_adds {
            rx_add_thread(&mut cur, insts, add_pc, input, p);
        }
        cur.clear();
        std::mem::swap(&mut cur, &mut nxt);
        p += 1;
        if p > input.len() + 1 { break; }
    }
    best
}

fn rx_add_thread(threads: &mut Vec<usize>, insts: &[RxInst], pc: usize, input: &[char], pos: usize) {
    if pc >= insts.len() || threads.contains(&pc) { return; }
    match &insts[pc] {
        RxInst::Split(a, b) => { rx_add_thread(threads, insts, *a, input, pos); rx_add_thread(threads, insts, *b, input, pos); }
        RxInst::Jump(t) => { rx_add_thread(threads, insts, *t, input, pos); }
        RxInst::AnchorStart => { if pos == 0 { rx_add_thread(threads, insts, pc + 1, input, pos); } }
        _ => { threads.push(pc); }
    }
}

fn rx_search(insts: &[RxInst], input: &str, ci: bool) -> bool {
    let chars: Vec<char> = input.chars().collect();
    for s in 0..=chars.len() {
        if rx_match_at(insts, &chars, s, ci).is_some() { return true; }
    }
    false
}

fn rx_find_all(insts: &[RxInst], input: &str, ci: bool) -> Vec<String> {
    let chars: Vec<char> = input.chars().collect();
    let mut results = Vec::new();
    let mut p = 0;
    while p <= chars.len() {
        if let Some(end) = rx_match_at(insts, &chars, p, ci) {
            if end > p { results.push(chars[p..end].iter().collect()); p = end; continue; }
        }
        p += 1;
    }
    results
}

fn rx_replace_all(insts: &[RxInst], input: &str, repl: &str, ci: bool) -> String {
    let chars: Vec<char> = input.chars().collect();
    let mut result = String::new();
    let mut p = 0;
    while p < chars.len() {
        if let Some(end) = rx_match_at(insts, &chars, p, ci) {
            if end > p { result.push_str(repl); p = end; continue; }
        }
        result.push(chars[p]);
        p += 1;
    }
    result
}

fn rx_split(insts: &[RxInst], input: &str, ci: bool) -> Vec<String> {
    let chars: Vec<char> = input.chars().collect();
    let mut parts = Vec::new();
    let mut last = 0;
    let mut p = 0;
    while p < chars.len() {
        if let Some(end) = rx_match_at(insts, &chars, p, ci) {
            if end > p { parts.push(chars[last..p].iter().collect()); last = end; p = end; continue; }
        }
        p += 1;
    }
    parts.push(chars[last..].iter().collect());
    parts
}

fn rx_get_flags(flags: &Value) -> bool {
    match flags { Value::Str(f) => f.contains('i'), _ => false }
}

fn regex_match_val(string: &Value, pattern: &Value, flags: &Value) -> Value {
    let s = match string { Value::Str(st) => st.clone(), _ => panic!("regex: string must be a string") };
    let p = match pattern { Value::Str(st) => st.clone(), _ => panic!("regex: pattern must be a string") };
    let ci = rx_get_flags(flags);
    let insts = rx_compile(&p, ci);
    Value::Bool(rx_search(&insts, &s, ci))
}

fn regex_find_all_val(string: &Value, pattern: &Value, flags: &Value) -> Value {
    let s = match string { Value::Str(st) => st.clone(), _ => panic!("regex: string must be a string") };
    let p = match pattern { Value::Str(st) => st.clone(), _ => panic!("regex: pattern must be a string") };
    let ci = rx_get_flags(flags);
    let insts = rx_compile(&p, ci);
    let matches = rx_find_all(&insts, &s, ci);
    make_array(matches.into_iter().map(|m| Value::Str(m)).collect())
}

fn regex_replace_val(string: &Value, pattern: &Value, replacement: &Value, flags: &Value) -> Value {
    let s = match string { Value::Str(st) => st.clone(), _ => panic!("regex: string must be a string") };
    let p = match pattern { Value::Str(st) => st.clone(), _ => panic!("regex: pattern must be a string") };
    let r = match replacement { Value::Str(st) => st.clone(), _ => panic!("regex: replacement must be a string") };
    let ci = rx_get_flags(flags);
    let insts = rx_compile(&p, ci);
    Value::Str(rx_replace_all(&insts, &s, &r, ci))
}

fn regex_split_val(string: &Value, pattern: &Value, flags: &Value) -> Value {
    let s = match string { Value::Str(st) => st.clone(), _ => panic!("regex: string must be a string") };
    let p = match pattern { Value::Str(st) => st.clone(), _ => panic!("regex: pattern must be a string") };
    let ci = rx_get_flags(flags);
    let insts = rx_compile(&p, ci);
    make_array(rx_split(&insts, &s, ci).into_iter().map(|p| Value::Str(p)).collect())
}

// ============================================================================
// Range helper (for For loops)
// ============================================================================

fn make_range(from: i64, to: i64, inclusive: bool) -> Vec<i64> {
    if inclusive {
        (from..=to).collect()
    } else {
        (from..to).collect()
    }
}

fn make_range_step(from: i64, to: i64, step: i64, inclusive: bool) -> Vec<i64> {
    let mut result = Vec::new();
    if step > 0 {
        let mut i = from;
        while if inclusive { i <= to } else { i < to } {
            result.push(i);
            i += step;
        }
    } else if step < 0 {
        let mut i = from;
        while if inclusive { i >= to } else { i > to } {
            result.push(i);
            i += step;
        }
    } else {
        panic!("range step cannot be zero");
    }
    result
}

// ============================================================================
// Exception handling support
// ============================================================================

/// CoreIL runtime error for Throw statements
#[derive(Clone, Debug)]
struct CoreILError {
    message: String,
}

impl fmt::Display for CoreILError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}

// ============================================================================
// Type checking helpers
// ============================================================================

fn is_none(v: &Value) -> bool {
    matches!(v, Value::None)
}

fn is_int(v: &Value) -> bool {
    matches!(v, Value::Int(_))
}

fn is_float(v: &Value) -> bool {
    matches!(v, Value::Float(_))
}

fn is_string(v: &Value) -> bool {
    matches!(v, Value::Str(_))
}

fn is_bool(v: &Value) -> bool {
    matches!(v, Value::Bool(_))
}

fn is_array(v: &Value) -> bool {
    matches!(v, Value::Array(_))
}

fn is_map(v: &Value) -> bool {
    matches!(v, Value::Map(_))
}

fn is_tuple(v: &Value) -> bool {
    matches!(v, Value::Tuple(_))
}

fn is_set(v: &Value) -> bool {
    matches!(v, Value::Set(_))
}

fn is_record(v: &Value) -> bool {
    matches!(v, Value::Record(_))
}

// ============================================================================
// Conversion helper: Value to i64 (for use in range/loop constructs)
// ============================================================================

fn value_to_i64(v: &Value) -> i64 {
    as_int(v)
}

fn value_to_f64(v: &Value) -> f64 {
    as_float(v)
}

// ============================================================================
// Type Conversions (v1.9) - reject bools for int/float, match interpreter
// ============================================================================

fn value_to_int(v: &Value) -> Value {
    match v {
        Value::Int(n) => Value::Int(*n),
        Value::Float(f) => Value::Int(*f as i64),
        Value::Str(s) => {
            match s.parse::<i64>() {
                Ok(n) => Value::Int(n),
                Err(_) => panic!("runtime error: cannot convert string '{}' to int", s),
            }
        }
        _ => panic!("runtime error: cannot convert {} to int", type_name(v)),
    }
}

fn value_to_float(v: &Value) -> Value {
    match v {
        Value::Float(f) => Value::Float(*f),
        Value::Int(n) => Value::Float(*n as f64),
        Value::Str(s) => {
            match s.parse::<f64>() {
                Ok(f) => Value::Float(f),
                Err(_) => panic!("runtime error: cannot convert string '{}' to float", s),
            }
        }
        _ => panic!("runtime error: cannot convert {} to float", type_name(v)),
    }
}

fn value_to_string_convert(v: &Value) -> Value {
    Value::Str(format_value(v))
}
