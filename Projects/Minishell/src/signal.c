#include "minishell.h"

void sigint_handler(int signum) {
    (void)signum;
    write(STDOUT_FILENO, "\n", 1);
}

void sigquit_handler(int signum) {
    (void)signum;
    exit(0);
}
