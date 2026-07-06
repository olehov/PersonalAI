#ifndef MINISHELL_H
# define MINISHELL_H

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct s_env {
    char	*name;
    char	*value;
} t_env;

typedef struct s_minishell {
    int			exit_status;
    char		**env;
    char		**history;
    int			history_size;
    int			history_index;
} t_minishell;

extern t_minishell *g_minishell;

int init_minishell(int ac, char **av);
void print_env(void);
char	*get_next_token(char *line, char delimiter);

#endif
