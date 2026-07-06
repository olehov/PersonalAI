#include <stdio.h>
#include "minishell.h"
#include "signals.h"

void interactive_handler(signal_t sig) {
  printf("\nCtrl-%c pressed.\n", sig->signum);
  // Add your code here to handle Ctrl-C and Ctrl-\ signals.
}