class Solution(object):
    def minCost(self, n, cost):
        """
        :type n: int
        :type cost: List[List[int]]
        :rtype: int
        """

        INF = 10**18   # safely larger than any possible cost

        dp = [[INF] * 3 for _ in range(3)]

        # Initialize first pair (0, n-1)
        for c1 in range(3):
            for c2 in range(3):
                if c1 != c2:
                    dp[c1][c2] = cost[0][c1] + cost[n - 1][c2]

        # Process remaining pairs
        for i in range(1, n // 2):
            new_dp = [[INF] * 3 for _ in range(3)]

            for pc1 in range(3):
                for pc2 in range(3):
                    if dp[pc1][pc2] == INF:
                        continue

                    for nc1 in range(3):
                        for nc2 in range(3):
                            if (
                                nc1 != nc2 and      # equidistant constraint
                                nc1 != pc1 and      # left adjacency
                                nc2 != pc2          # right adjacency
                            ):
                                new_dp[nc1][nc2] = min(
                                    new_dp[nc1][nc2],
                                    dp[pc1][pc2]
                                    + cost[i][nc1]
                                    + cost[n - 1 - i][nc2]
                                )

            dp = new_dp

        return min(
            dp[c1][c2]
            for c1 in range(3)
            for c2 in range(3)
            if c1 != c2
        )

