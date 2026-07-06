#include "minishell.h"
#include <readline/readline.h>
#include <stdio.h>
#include <stdlib.h>

int main(int ac, char **av) {
    init_minishell(ac, av);
    while (1) {
        print_prompt();
        char *input = readline(">");
        if (!input)
            break;
        else
            process_command(input);
    }
}

void sigint_handler(int signum) {
    (void)signum;
    write(STDOUT_FILENO, "\n", 1);
}

void init_minishell(t_env **envp) {
    g_minishell = malloc(sizeof(t_minishell));
    if (!g_minishell)
        exit(1);
    signal(SIGINT, sigint_handler);
    signal(SIGQUIT, SIG_IGN); // Ignore SIGQUIT to prevent core dumps
}

void print_prompt(void) {
    char	buf[PATH_MAX];
    getcwd(buf, sizeof(buf));
    write(STDOUT_FILENO, buf, strlen(buf));
    write(STDOUT_FILENO, "$ ", 2);
}
