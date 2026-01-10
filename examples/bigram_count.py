arr = ["a", "b", "c", "a", "b"]
counts = {}
i = 0
while (i < (len(arr) - 1)):
    pair = (arr[i], arr[(i + 1)])
    counts[pair] = (counts.get(pair, 0) + 1)
    i = (i + 1)
print(counts)
