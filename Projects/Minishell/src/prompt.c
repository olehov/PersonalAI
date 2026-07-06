#include "minishell.h"

void print_prompt(void) {
    char	buf[PATH_MAX];
    getcwd(buf, sizeof(buf));
    write(STDOUT_FILENO, buf, strlen(buf));
    write(STDOUT_FILENO, "$ ", 2);
}
