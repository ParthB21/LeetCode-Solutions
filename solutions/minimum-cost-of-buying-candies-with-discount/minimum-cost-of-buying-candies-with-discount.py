# 2248. Minimum Cost of Buying Candies With Discount
# https://leetcode.com/problems/minimum-cost-of-buying-candies-with-discount/
# Accepted 2026-06-02
# Runtime 0 ms (beats 100.0%) | Memory 12.4 MB (beats 53.6%)

class Solution(object):
        def minimumCost(self, cost):
                """
                :type cost: List[int]
                :rtype: int
                """
                sum=0
                cost.sort(reverse=True)
                for i in range(0,len(cost)):
                    if (i+1)%3!=0:
                        sum=sum+cost[i]
                return sum
