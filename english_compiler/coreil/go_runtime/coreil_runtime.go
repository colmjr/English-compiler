package main

import (
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
)

// ============================================================================
// Core IL Runtime for Go
// ============================================================================

// ValueType represents the type tag for Core IL values.
type ValueType int

const (
	TypeNone ValueType = iota
	TypeInt
	TypeFloat
	TypeBool
	TypeStr
	TypeArray
	TypeMap
	TypeTuple
	TypeRecord
	TypeSet
	TypeDeque
	TypeHeap
)

// Value is the universal value type for Core IL.
type Value struct {
	Type ValueType
	data interface{}
}

// Constructors

var ValueNone = Value{Type: TypeNone}

func ValueInt(v int64) Value    { return Value{Type: TypeInt, data: v} }
func ValueFloat(v float64) Value { return Value{Type: TypeFloat, data: v} }
func ValueBool(v bool) Value    { return Value{Type: TypeBool, data: v} }
func ValueStr(v string) Value   { return Value{Type: TypeStr, data: v} }

func ValueArray(items []Value) Value {
	arr := make([]Value, len(items))
	copy(arr, items)
	return Value{Type: TypeArray, data: &arr}
}

func ValueTupleNew(items []Value) Value {
	t := make([]Value, len(items))
	copy(t, items)
	return Value{Type: TypeTuple, data: t}
}

// OrderedMap maintains insertion order.
type OrderedMap struct {
	keys   []string
	values map[string]Value
}

func NewOrderedMap() *OrderedMap {
	return &OrderedMap{keys: nil, values: make(map[string]Value)}
}

func (m *OrderedMap) Set(key string, val Value) {
	if _, exists := m.values[key]; !exists {
		m.keys = append(m.keys, key)
	}
	m.values[key] = val
}

func (m *OrderedMap) Get(key string) (Value, bool) {
	v, ok := m.values[key]
	return v, ok
}

func (m *OrderedMap) Keys() []string {
	result := make([]string, len(m.keys))
	copy(result, m.keys)
	return result
}

func ValueMapNew(pairs []struct{ K, V Value }) Value {
	om := NewOrderedMap()
	for _, p := range pairs {
		om.Set(asString(p.K), p.V)
	}
	return Value{Type: TypeMap, data: om}
}

func ValueMapEmpty() Value {
	return Value{Type: TypeMap, data: NewOrderedMap()}
}

// Record
type Record struct {
	fields map[string]Value
	order  []string
}

func NewRecord(pairs []struct{ Name string; Val Value }) *Record {
	r := &Record{fields: make(map[string]Value), order: nil}
	for _, p := range pairs {
		r.fields[p.Name] = p.Val
		r.order = append(r.order, p.Name)
	}
	return r
}

func ValueRecordNew(pairs []struct{ Name string; Val Value }) Value {
	return Value{Type: TypeRecord, data: NewRecord(pairs)}
}

// Set (uses map[string]Value for dedup by formatted value)
type ValueSet struct {
	items map[string]Value
}

func NewValueSet() *ValueSet {
	return &ValueSet{items: make(map[string]Value)}
}

func ValueSetNew(items []Value) Value {
	s := NewValueSet()
	for _, item := range items {
		s.items[formatValue(item)] = item
	}
	return Value{Type: TypeSet, data: s}
}

// Deque
type Deque struct {
	items []Value
}

func NewDeque() *Deque {
	return &Deque{}
}

func ValueDequeNew() Value {
	return Value{Type: TypeDeque, data: NewDeque()}
}

// Heap (min-heap by priority)
type HeapItem struct {
	priority float64
	value    Value
}

type MinHeap struct {
	items []HeapItem
}

func NewMinHeap() *MinHeap {
	return &MinHeap{}
}

func (h *MinHeap) Len() int            { return len(h.items) }
func (h *MinHeap) Less(i, j int) bool  { return h.items[i].priority < h.items[j].priority }
func (h *MinHeap) Swap(i, j int)       { h.items[i], h.items[j] = h.items[j], h.items[i] }
func (h *MinHeap) Push(x HeapItem) {
	h.items = append(h.items, x)
	h.siftUp(len(h.items) - 1)
}
func (h *MinHeap) Pop() HeapItem {
	if len(h.items) == 0 {
		panic("runtime error: heap is empty")
	}
	top := h.items[0]
	n := len(h.items) - 1
	h.items[0] = h.items[n]
	h.items = h.items[:n]
	if n > 0 {
		h.siftDown(0)
	}
	return top
}
func (h *MinHeap) Peek() Value {
	if len(h.items) == 0 {
		panic("runtime error: heap is empty")
	}
	return h.items[0].value
}
func (h *MinHeap) siftUp(i int) {
	for i > 0 {
		parent := (i - 1) / 2
		if h.items[parent].priority <= h.items[i].priority {
			break
		}
		h.Swap(i, parent)
		i = parent
	}
}
func (h *MinHeap) siftDown(i int) {
	n := len(h.items)
	for {
		smallest := i
		l, r := 2*i+1, 2*i+2
		if l < n && h.items[l].priority < h.items[smallest].priority {
			smallest = l
		}
		if r < n && h.items[r].priority < h.items[smallest].priority {
			smallest = r
		}
		if smallest == i {
			break
		}
		h.Swap(i, smallest)
		i = smallest
	}
}

func ValueHeapNew() Value {
	return Value{Type: TypeHeap, data: NewMinHeap()}
}

// ============================================================================
// Value accessors
// ============================================================================

func asInt(v Value) int64 {
	switch v.Type {
	case TypeInt:
		return v.data.(int64)
	case TypeFloat:
		return int64(v.data.(float64))
	case TypeBool:
		if v.data.(bool) {
			return 1
		}
		return 0
	default:
		panic(fmt.Sprintf("runtime error: expected int, got %s", typeName(v)))
	}
}

func asFloat(v Value) float64 {
	switch v.Type {
	case TypeInt:
		return float64(v.data.(int64))
	case TypeFloat:
		return v.data.(float64)
	default:
		panic(fmt.Sprintf("runtime error: expected number, got %s", typeName(v)))
	}
}

func asString(v Value) string {
	if v.Type == TypeStr {
		return v.data.(string)
	}
	panic(fmt.Sprintf("runtime error: expected string, got %s", typeName(v)))
}

func asBool(v Value) bool {
	if v.Type == TypeBool {
		return v.data.(bool)
	}
	panic(fmt.Sprintf("runtime error: expected bool, got %s", typeName(v)))
}

func asArray(v Value) *[]Value {
	if v.Type == TypeArray {
		return v.data.(*[]Value)
	}
	panic(fmt.Sprintf("runtime error: expected array, got %s", typeName(v)))
}

func asMap(v Value) *OrderedMap {
	if v.Type == TypeMap {
		return v.data.(*OrderedMap)
	}
	panic(fmt.Sprintf("runtime error: expected map, got %s", typeName(v)))
}

func asRecord(v Value) *Record {
	if v.Type == TypeRecord {
		return v.data.(*Record)
	}
	panic(fmt.Sprintf("runtime error: expected record, got %s", typeName(v)))
}

func asSet(v Value) *ValueSet {
	if v.Type == TypeSet {
		return v.data.(*ValueSet)
	}
	panic(fmt.Sprintf("runtime error: expected set, got %s", typeName(v)))
}

func asDeque(v Value) *Deque {
	if v.Type == TypeDeque {
		return v.data.(*Deque)
	}
	panic(fmt.Sprintf("runtime error: expected deque, got %s", typeName(v)))
}

func asHeap(v Value) *MinHeap {
	if v.Type == TypeHeap {
		return v.data.(*MinHeap)
	}
	panic(fmt.Sprintf("runtime error: expected heap, got %s", typeName(v)))
}

func typeName(v Value) string {
	switch v.Type {
	case TypeNone:
		return "None"
	case TypeInt:
		return "int"
	case TypeFloat:
		return "float"
	case TypeBool:
		return "bool"
	case TypeStr:
		return "str"
	case TypeArray:
		return "array"
	case TypeMap:
		return "map"
	case TypeTuple:
		return "tuple"
	case TypeRecord:
		return "record"
	case TypeSet:
		return "set"
	case TypeDeque:
		return "deque"
	case TypeHeap:
		return "heap"
	default:
		return "unknown"
	}
}

// ============================================================================
// Truthiness
// ============================================================================

func isTruthy(v Value) bool {
	switch v.Type {
	case TypeNone:
		return false
	case TypeBool:
		return v.data.(bool)
	case TypeInt:
		return v.data.(int64) != 0
	case TypeFloat:
		return v.data.(float64) != 0
	case TypeStr:
		return v.data.(string) != ""
	case TypeArray:
		return len(*v.data.(*[]Value)) > 0
	case TypeMap:
		return len(v.data.(*OrderedMap).keys) > 0
	default:
		return true
	}
}

// ============================================================================
// Formatting / Printing
// ============================================================================

func formatValue(v Value) string {
	switch v.Type {
	case TypeNone:
		return "None"
	case TypeInt:
		return strconv.FormatInt(v.data.(int64), 10)
	case TypeFloat:
		f := v.data.(float64)
		s := strconv.FormatFloat(f, 'f', -1, 64)
		if !strings.Contains(s, ".") {
			s += ".0"
		}
		return s
	case TypeBool:
		if v.data.(bool) {
			return "True"
		}
		return "False"
	case TypeStr:
		return v.data.(string)
	case TypeArray:
		arr := *v.data.(*[]Value)
		parts := make([]string, len(arr))
		for i, item := range arr {
			parts[i] = reprValue(item)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case TypeTuple:
		items := v.data.([]Value)
		parts := make([]string, len(items))
		for i, item := range items {
			parts[i] = reprValue(item)
		}
		return "(" + strings.Join(parts, ", ") + ")"
	case TypeMap:
		om := v.data.(*OrderedMap)
		parts := make([]string, len(om.keys))
		for i, k := range om.keys {
			parts[i] = fmt.Sprintf("'%s': %s", k, reprValue(om.values[k]))
		}
		return "{" + strings.Join(parts, ", ") + "}"
	case TypeRecord:
		r := v.data.(*Record)
		parts := make([]string, len(r.order))
		for i, name := range r.order {
			parts[i] = fmt.Sprintf("%s=%s", name, reprValue(r.fields[name]))
		}
		return "Record(" + strings.Join(parts, ", ") + ")"
	case TypeSet:
		s := v.data.(*ValueSet)
		keys := make([]string, 0, len(s.items))
		for k := range s.items {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		parts := make([]string, len(keys))
		for i, k := range keys {
			parts[i] = reprValue(s.items[k])
		}
		return "{" + strings.Join(parts, ", ") + "}"
	default:
		return fmt.Sprintf("<%s>", typeName(v))
	}
}

func reprValue(v Value) string {
	if v.Type == TypeStr {
		return fmt.Sprintf("'%s'", v.data.(string))
	}
	return formatValue(v)
}

func coreilPrint(args []Value) {
	parts := make([]string, len(args))
	for i, arg := range args {
		parts[i] = formatValue(arg)
	}
	fmt.Println(strings.Join(parts, " "))
}

// ============================================================================
// Arithmetic / Comparison
// ============================================================================

func valueAdd(a, b Value) Value {
	if a.Type == TypeStr && b.Type == TypeStr {
		return ValueStr(a.data.(string) + b.data.(string))
	}
	if a.Type == TypeInt && b.Type == TypeInt {
		return ValueInt(a.data.(int64) + b.data.(int64))
	}
	if (a.Type == TypeInt || a.Type == TypeFloat) && (b.Type == TypeInt || b.Type == TypeFloat) {
		return ValueFloat(asFloat(a) + asFloat(b))
	}
	panic(fmt.Sprintf("runtime error: cannot add %s and %s", typeName(a), typeName(b)))
}

func valueSubtract(a, b Value) Value {
	if a.Type == TypeInt && b.Type == TypeInt {
		return ValueInt(a.data.(int64) - b.data.(int64))
	}
	if (a.Type == TypeInt || a.Type == TypeFloat) && (b.Type == TypeInt || b.Type == TypeFloat) {
		return ValueFloat(asFloat(a) - asFloat(b))
	}
	panic(fmt.Sprintf("runtime error: cannot subtract %s and %s", typeName(a), typeName(b)))
}

func valueMultiply(a, b Value) Value {
	if a.Type == TypeInt && b.Type == TypeInt {
		return ValueInt(a.data.(int64) * b.data.(int64))
	}
	if (a.Type == TypeInt || a.Type == TypeFloat) && (b.Type == TypeInt || b.Type == TypeFloat) {
		return ValueFloat(asFloat(a) * asFloat(b))
	}
	panic(fmt.Sprintf("runtime error: cannot multiply %s and %s", typeName(a), typeName(b)))
}

func valueDivide(a, b Value) Value {
	if a.Type == TypeInt && b.Type == TypeInt {
		bv := b.data.(int64)
		if bv == 0 {
			panic("runtime error: division by zero")
		}
		return ValueInt(a.data.(int64) / bv)
	}
	if (a.Type == TypeInt || a.Type == TypeFloat) && (b.Type == TypeInt || b.Type == TypeFloat) {
		bv := asFloat(b)
		if bv == 0 {
			panic("runtime error: division by zero")
		}
		return ValueFloat(asFloat(a) / bv)
	}
	panic(fmt.Sprintf("runtime error: cannot divide %s by %s", typeName(a), typeName(b)))
}

func valueModulo(a, b Value) Value {
	if a.Type == TypeInt && b.Type == TypeInt {
		bv := b.data.(int64)
		if bv == 0 {
			panic("runtime error: modulo by zero")
		}
		result := a.data.(int64) % bv
		// Python-style modulo (result has same sign as divisor)
		if result != 0 && (result < 0) != (bv < 0) {
			result += bv
		}
		return ValueInt(result)
	}
	if (a.Type == TypeInt || a.Type == TypeFloat) && (b.Type == TypeInt || b.Type == TypeFloat) {
		bv := asFloat(b)
		if bv == 0 {
			panic("runtime error: modulo by zero")
		}
		return ValueFloat(math.Mod(asFloat(a), bv))
	}
	panic(fmt.Sprintf("runtime error: cannot modulo %s and %s", typeName(a), typeName(b)))
}

func valueEqual(a, b Value) bool {
	if a.Type != b.Type {
		// Allow int/float comparison
		if (a.Type == TypeInt || a.Type == TypeFloat) && (b.Type == TypeInt || b.Type == TypeFloat) {
			return asFloat(a) == asFloat(b)
		}
		return false
	}
	switch a.Type {
	case TypeNone:
		return true
	case TypeInt:
		return a.data.(int64) == b.data.(int64)
	case TypeFloat:
		return a.data.(float64) == b.data.(float64)
	case TypeBool:
		return a.data.(bool) == b.data.(bool)
	case TypeStr:
		return a.data.(string) == b.data.(string)
	case TypeArray:
		aa, ba := *a.data.(*[]Value), *b.data.(*[]Value)
		if len(aa) != len(ba) {
			return false
		}
		for i := range aa {
			if !valueEqual(aa[i], ba[i]) {
				return false
			}
		}
		return true
	default:
		return false
	}
}

func valueLessThan(a, b Value) bool {
	if a.Type == TypeInt && b.Type == TypeInt {
		return a.data.(int64) < b.data.(int64)
	}
	if (a.Type == TypeInt || a.Type == TypeFloat) && (b.Type == TypeInt || b.Type == TypeFloat) {
		return asFloat(a) < asFloat(b)
	}
	if a.Type == TypeStr && b.Type == TypeStr {
		return a.data.(string) < b.data.(string)
	}
	panic(fmt.Sprintf("runtime error: cannot compare %s and %s", typeName(a), typeName(b)))
}

func valueLessThanOrEqual(a, b Value) bool {
	return valueLessThan(a, b) || valueEqual(a, b)
}

func valueGreaterThan(a, b Value) bool {
	return !valueLessThanOrEqual(a, b)
}

func valueGreaterThanOrEqual(a, b Value) bool {
	return !valueLessThan(a, b)
}

func logicalNot(v Value) Value {
	return ValueBool(!isTruthy(v))
}

// ============================================================================
// Array operations
// ============================================================================

func arrayIndex(base, index Value) Value {
	arr := asArray(base)
	idx := asInt(index)
	length := int64(len(*arr))
	if idx < 0 {
		idx += length
	}
	if idx < 0 || idx >= length {
		panic(fmt.Sprintf("runtime error: index %d out of range for array of length %d", idx, length))
	}
	return (*arr)[idx]
}

func arraySetIndex(base, index, value Value) {
	arr := asArray(base)
	idx := asInt(index)
	length := int64(len(*arr))
	if idx < 0 {
		idx += length
	}
	if idx < 0 || idx >= length {
		panic(fmt.Sprintf("runtime error: index %d out of range for array of length %d", idx, length))
	}
	(*arr)[idx] = value
}

func arrayLength(base Value) Value {
	arr := asArray(base)
	return ValueInt(int64(len(*arr)))
}

func arrayPush(base, value Value) {
	arr := asArray(base)
	*arr = append(*arr, value)
}

func arraySlice(base, start, end Value) Value {
	arr := asArray(base)
	length := int64(len(*arr))
	s := asInt(start)
	e := asInt(end)

	// Handle negative indices
	if s < 0 {
		s += length
	}
	if e < 0 {
		e += length
	}

	// Clamp to bounds
	if s < 0 {
		s = 0
	}
	if e > length {
		e = length
	}
	if s > length {
		s = length
	}
	if e < s {
		return ValueArray(nil)
	}

	result := make([]Value, e-s)
	copy(result, (*arr)[s:e])
	return ValueArray(result)
}

// ============================================================================
// Map operations
// ============================================================================

func mapGet(base, key Value) Value {
	m := asMap(base)
	k := asString(key)
	v, ok := m.Get(k)
	if !ok {
		panic(fmt.Sprintf("runtime error: key '%s' not found", k))
	}
	return v
}

func mapGetDefault(base, key, defaultVal Value) Value {
	m := asMap(base)
	k := asString(key)
	v, ok := m.Get(k)
	if !ok {
		return defaultVal
	}
	return v
}

func mapSet(base, key, value Value) {
	m := asMap(base)
	k := asString(key)
	m.Set(k, value)
}

func mapKeys(base Value) Value {
	m := asMap(base)
	keys := m.Keys()
	result := make([]Value, len(keys))
	for i, k := range keys {
		result[i] = ValueStr(k)
	}
	return ValueArray(result)
}

// ============================================================================
// Record operations
// ============================================================================

func recordGetField(base Value, name string) Value {
	r := asRecord(base)
	v, ok := r.fields[name]
	if !ok {
		panic(fmt.Sprintf("runtime error: field '%s' not found", name))
	}
	return v
}

func recordSetField(base Value, name string, value Value) {
	r := asRecord(base)
	if _, ok := r.fields[name]; !ok {
		r.order = append(r.order, name)
	}
	r.fields[name] = value
}

// ============================================================================
// String operations
// ============================================================================

func stringLength(base Value) Value {
	s := asString(base)
	return ValueInt(int64(len(s)))
}

func stringSubstring(base, start, end Value) Value {
	s := asString(base)
	si := int(asInt(start))
	ei := int(asInt(end))
	if si < 0 {
		si = 0
	}
	if ei > len(s) {
		ei = len(s)
	}
	if si > ei {
		return ValueStr("")
	}
	return ValueStr(s[si:ei])
}

func stringCharAt(base, index Value) Value {
	s := asString(base)
	idx := int(asInt(index))
	if idx < 0 || idx >= len(s) {
		panic(fmt.Sprintf("runtime error: string index %d out of range", idx))
	}
	return ValueStr(string(s[idx]))
}

func stringJoin(sep, items Value) Value {
	s := asString(sep)
	arr := asArray(items)
	parts := make([]string, len(*arr))
	for i, item := range *arr {
		parts[i] = formatValue(item)
	}
	return ValueStr(strings.Join(parts, s))
}

func stringSplit(base, delimiter Value) Value {
	s := asString(base)
	d := asString(delimiter)
	parts := strings.Split(s, d)
	result := make([]Value, len(parts))
	for i, p := range parts {
		result[i] = ValueStr(p)
	}
	return ValueArray(result)
}

func stringTrim(base Value) Value {
	return ValueStr(strings.TrimSpace(asString(base)))
}

func stringUpper(base Value) Value {
	return ValueStr(strings.ToUpper(asString(base)))
}

func stringLower(base Value) Value {
	return ValueStr(strings.ToLower(asString(base)))
}

func stringStartsWith(base, prefix Value) Value {
	return ValueBool(strings.HasPrefix(asString(base), asString(prefix)))
}

func stringEndsWith(base, suffix Value) Value {
	return ValueBool(strings.HasSuffix(asString(base), asString(suffix)))
}

func stringContains(base, substring Value) Value {
	return ValueBool(strings.Contains(asString(base), asString(substring)))
}

func stringReplaceFn(base, old, new_ Value) Value {
	return ValueStr(strings.ReplaceAll(asString(base), asString(old), asString(new_)))
}

// ============================================================================
// Set operations
// ============================================================================

func setHas(base, value Value) Value {
	s := asSet(base)
	_, ok := s.items[formatValue(value)]
	return ValueBool(ok)
}

func setAdd(base, value Value) {
	s := asSet(base)
	s.items[formatValue(value)] = value
}

func setRemove(base, value Value) {
	s := asSet(base)
	delete(s.items, formatValue(value))
}

func setSize(base Value) Value {
	s := asSet(base)
	return ValueInt(int64(len(s.items)))
}

// ============================================================================
// Deque operations
// ============================================================================

func dequeSize(base Value) Value {
	d := asDeque(base)
	return ValueInt(int64(len(d.items)))
}

func dequePushBack(base, value Value) {
	d := asDeque(base)
	d.items = append(d.items, value)
}

func dequePushFront(base, value Value) {
	d := asDeque(base)
	d.items = append([]Value{value}, d.items...)
}

func dequePopFront(base Value) Value {
	d := asDeque(base)
	if len(d.items) == 0 {
		panic("runtime error: deque is empty")
	}
	v := d.items[0]
	d.items = d.items[1:]
	return v
}

func dequePopBack(base Value) Value {
	d := asDeque(base)
	if len(d.items) == 0 {
		panic("runtime error: deque is empty")
	}
	v := d.items[len(d.items)-1]
	d.items = d.items[:len(d.items)-1]
	return v
}

// ============================================================================
// Heap operations
// ============================================================================

func heapSize(base Value) Value {
	h := asHeap(base)
	return ValueInt(int64(h.Len()))
}

func heapPeek(base Value) Value {
	h := asHeap(base)
	return h.Peek()
}

func heapPush(base, priority, value Value) {
	h := asHeap(base)
	p := asFloat(priority)
	h.Push(HeapItem{priority: p, value: value})
}

func heapPop(base Value) Value {
	h := asHeap(base)
	item := h.Pop()
	return item.value
}

// ============================================================================
// Math operations
// ============================================================================

func mathSin(v Value) Value   { return ValueFloat(math.Sin(asFloat(v))) }
func mathCos(v Value) Value   { return ValueFloat(math.Cos(asFloat(v))) }
func mathTan(v Value) Value   { return ValueFloat(math.Tan(asFloat(v))) }
func mathSqrt(v Value) Value  { return ValueFloat(math.Sqrt(asFloat(v))) }
func mathFloor(v Value) Value { return ValueFloat(math.Floor(asFloat(v))) }
func mathCeil(v Value) Value  { return ValueFloat(math.Ceil(asFloat(v))) }
func mathLog(v Value) Value   { return ValueFloat(math.Log(asFloat(v))) }
func mathExp(v Value) Value   { return ValueFloat(math.Exp(asFloat(v))) }
func mathPow(base, exp Value) Value {
	return ValueFloat(math.Pow(asFloat(base), asFloat(exp)))
}

func mathAbs(v Value) Value {
	switch v.Type {
	case TypeInt:
		n := v.data.(int64)
		if n < 0 {
			return ValueInt(-n)
		}
		return v
	case TypeFloat:
		return ValueFloat(math.Abs(v.data.(float64)))
	default:
		panic(fmt.Sprintf("runtime error: abs requires a number, got %s", typeName(v)))
	}
}

func mathPi() Value { return ValueFloat(math.Pi) }
func mathE() Value  { return ValueFloat(math.E) }

// ============================================================================
// Type conversions
// ============================================================================

func valueToInt(v Value) Value {
	switch v.Type {
	case TypeInt:
		return v
	case TypeFloat:
		return ValueInt(int64(v.data.(float64)))
	case TypeBool:
		if v.data.(bool) {
			return ValueInt(1)
		}
		return ValueInt(0)
	case TypeStr:
		n, err := strconv.ParseInt(v.data.(string), 10, 64)
		if err != nil {
			panic(fmt.Sprintf("runtime error: cannot convert string '%s' to int", v.data.(string)))
		}
		return ValueInt(n)
	default:
		panic(fmt.Sprintf("runtime error: cannot convert %s to int", typeName(v)))
	}
}

func valueToFloat(v Value) Value {
	switch v.Type {
	case TypeFloat:
		return v
	case TypeInt:
		return ValueFloat(float64(v.data.(int64)))
	case TypeBool:
		if v.data.(bool) {
			return ValueFloat(1.0)
		}
		return ValueFloat(0.0)
	case TypeStr:
		f, err := strconv.ParseFloat(v.data.(string), 64)
		if err != nil {
			panic(fmt.Sprintf("runtime error: cannot convert string '%s' to float", v.data.(string)))
		}
		return ValueFloat(f)
	default:
		panic(fmt.Sprintf("runtime error: cannot convert %s to float", typeName(v)))
	}
}

func valueToStringConvert(v Value) Value {
	return ValueStr(formatValue(v))
}

// Ensure all imports are used
var _ = sort.Strings
