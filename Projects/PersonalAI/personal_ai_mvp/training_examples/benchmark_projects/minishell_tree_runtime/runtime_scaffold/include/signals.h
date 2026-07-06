#include <signal.h>
#include "minishell.h"

void handle_signals(int signum) {
    if (signum == SIGINT) {
        // Handle Ctrl-C (SIGINT) - Add your custom logic here
        write(STDOUT_FILENO, "\nCaught SIGINT.  Exiting.\n", strlen("\nCaught SIGINT.  Exiting.\n"));
        exit(0);
    } else if (signum == SIGQUIT) {
        // Handle Ctrl-`) (SIGQUIT) - Add your custom logic here
        write(STDOUT_FILENO, "\nCaught SIGQUIT.  Exiting.\n", strlen("\nCaught SIGQUIT.  Exiting.\n"));
        exit(0);
    }
}

int main() {
    // Register the signal handlers
    signal(SIGINT, handle_signals);
    signal(SIGQUIT, handle_signals);

    // Your shell implementation goes here...
    write(STDOUT_FILENO, "Minishell is running...\n", strlen("Minishell is running...\n"));

    return 0;
}