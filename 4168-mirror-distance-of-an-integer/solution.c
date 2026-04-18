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
