#include <stdio.h>
#include "builtins.h"

// Builtin dispatch table - minimal for now
typedef struct {
    int (*func)(char **);
} builtin_t;

builtin_t builtins[] = {
    { &do_cd, 1 },
    { &do_exit, 0 }
};

// Number of builtins
const int NUM_BUILTINS = sizeof(builtins) / sizeof(builtin_t);

/**
 *  do_cd - Changes the current directory.
 *  @args: Array of arguments to the builtin.
 *  Returns: 0 on success, other values on error.
 */
int do_cd(char **args) {
    if (args[1] == NULL) {
        return 0; // No argument, stay in current directory
    }

    // Implement cd logic here - simplified for now
    printf("do_cd: Changing to %s\n", args[1]);

    return 0;
}

/**
 *  do_exit - Exits the shell.
 *  @args: Array of arguments to the builtin.
 *  Returns: 0 on success, other values on error.
 */
int do_exit(char **args) {
    return 0; // Exit the shell
}