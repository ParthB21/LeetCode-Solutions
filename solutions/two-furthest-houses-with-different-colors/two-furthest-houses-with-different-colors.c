/*
 * 2199. Two Furthest Houses With Different Colors
 * https://leetcode.com/problems/two-furthest-houses-with-different-colors/
 * Accepted 2026-04-20
 * Runtime 0 ms (beats 100.0%) | Memory 8.7 MB (beats 100.0%)
 */

int maxDistance(int* colors, int colorsSize) {
    int x= 0;
    for (int j = colorsSize - 1; j > 0; j--) {
        if (colors[j] != colors[0]) {
            x = j;
            break;
        }
    }

    for (int i = 0; i < colorsSize - 1; i++) {
        if (colors[i] != colors[colorsSize - 1]) {
            int current_dist = (colorsSize - 1) - i;
            if (current_dist > x) {
                x = current_dist;
            }
            break;
        }
    }

    return x;
}
