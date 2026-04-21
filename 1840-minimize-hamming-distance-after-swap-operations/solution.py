from collections import defaultdict, Counter

class Solution(object):
    def minimumHammingDistance(self, source, target, allowedSwaps):
        n = len(source)
        parent = list(range(n))

        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        for u, v in allowedSwaps:
            root_u, root_v = find(u), find(v)
            if root_u != root_v:
                parent[root_u] = root_v

        components = defaultdict(list)
        for i in range(n):
            components[find(i)].append(i)

        hamming_distance = 0
        
        for indices in components.values():
            
            source_count = Counter(source[i] for i in indices)
            target_count = Counter(target[i] for i in indices)
            
            matches = sum((source_count & target_count).values())
            hamming_distance += (len(indices) - matches)

        return hamming_distance
