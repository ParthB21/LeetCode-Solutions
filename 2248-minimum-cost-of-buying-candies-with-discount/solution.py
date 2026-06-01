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
                                                                                                            
