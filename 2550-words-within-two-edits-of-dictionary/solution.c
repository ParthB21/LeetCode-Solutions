/**
 * Note: The returned array must be malloced, assume caller calls free().
 */
char** twoEditWords(char** queries, int queriesSize, char** dictionary, int dictionarySize, int* returnSize) {
    char** result = (char**)malloc(queriesSize * sizeof(char*));
    int count = 0;

    for (int i = 0; i< queriesSize; i++){
        char* q = queries[i];
        int len = strlen(q);
        bool matchFound = false;
        for (int j = 0; j< dictionarySize; j++){
            char* dWord = dictionary[j];
            int diffs = 0;
            for(int k = 0; k<len;k++){
                if(q[k]!=dWord[k]){
                    diffs++;
                }
                if (diffs>2) break;
                }
                if (diffs<=2){
                    matchFound = true;
                    break;
                }
            }
            if(matchFound){
                result[count] = (char*)malloc((len+1)*sizeof(char));
                strcpy(result[count], q);
                count++;
            }
        }
        *returnSize=count;
        return result;

    }

