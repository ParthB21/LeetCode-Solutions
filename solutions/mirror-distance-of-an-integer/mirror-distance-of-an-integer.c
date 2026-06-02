/*
 * 4168. Mirror Distance of an Integer
 * https://leetcode.com/problems/mirror-distance-of-an-integer/
 * Accepted 2026-04-18
 * Runtime 0 ms (beats 100.0%) | Memory 9.2 MB (beats 25.6%)
 */

#include<math.h>
#include <stdlib.h>
int mirrorDistance(int n) {
    int k = 0;
    int j = n;
    int rem;
    while(j!=0){
        rem = j % 10;
        k = k*10 + rem;
        j=j/10;
    }
    return(abs(k-n));
}
