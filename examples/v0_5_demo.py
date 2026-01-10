scores = {"Alice": 95, "Bob": 87}
alice_score = scores.get("Alice", 0)
print(alice_score)
charlie_score = scores.get("Charlie", 0)
print(charlie_score)
names = sorted(scores.keys())
print(names)
numbers = [1, 2]
numbers.append(3)
print(numbers)
tuple_key = ("x", "y")
coords = {("x", "y"): 42}
print(coords)
