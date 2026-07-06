# runtime_scaffold/include/builtins.h
#ifndef __MINISHELL_BUILTINS_H__
#define __MINISHELL_BUILTINS_H__

#include <stdio.h> // For printf (debugging)
// Define built-in commands here, or placeholder functions if not implemented yet.
// This is a minimal example and would be expanded upon in a full implementation.

// Example:  Implementation for 'exit' builtin
int builtin_exit(char **args) {
    return 0; // Exit successfully
}

// Example: Implementation for 'cd' builtin
int builtin_cd(char **args) {
    if (args[1] == NULL) {
        chdir("/"); // Change to root directory if no argument is provided
        return 0;
    }
    if (chdir(args[1]) != 0) {
        perror(args[1]); // Print error message if unable to change directory
        return 1;
    }
    return 0;
}

// Placeholder for other builtins...
int builtin_pwd() {
  printf("%s\n", getcwd(NULL, 0));
  return 0;
}


#endif /* __MINISHELL_BUILTINS_H__ */