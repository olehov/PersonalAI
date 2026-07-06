#include <stdio.h>
#include "minishell.h"

int main() {
  // Shell loop wiring - minimal implementation for scaffolding
  while (1) {
    char command[256];
    fgets(command, sizeof(command), stdin);
    if (strcmp(command, "exit") == 0) {
      break;
    }

    // Placeholder: Implement parsing and execution logic here
    printf("Command: %s\n", command);
  }
  return 0;
}