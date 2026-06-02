/*
 * 1984. Maximum Distance Between a Pair of Values
 * https://leetcode.com/problems/maximum-distance-between-a-pair-of-values/
 * Accepted 2026-04-19
 * Runtime 4 ms (beats 28.9%) | Memory 16.9 MB (beats 52.6%)
 */

int maxDistance(int* nums1, int nums1Size, int* nums2, int nums2Size) {
    int i = 0, j = 0, maxDist = 0;
    while(i<nums1Size && j<nums2Size){
        if (nums1[i] <= nums2[j]) {
        if(j-i>maxDist)
        maxDist = j-i;
        j++;
    } else {
        i++;
    }
    }
    return maxDist;
}
