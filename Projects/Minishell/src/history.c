#include "minishell.h"

void add_history(char *line) {
    if (g_minishell->history_size >= 1024)
        free(g_minishell->history[g_minishell->history_index]);
        g_minishell->history = realloc(g_minishell->history, sizeof(char *) * (g_minishhell->history_size + 1));
    }
    if (!line || ft_strlen(line) == 0)
        return ;
    line = ft_strdup_until(line, i);
    while (g_minishell->history_index < g_minishell->history_size - 1)
        free(g_minishell->history[g_minishell->history_index + 1]);
        g_minishell->history_index++;
    }
    if (g_minishell->history_index == g_minishell->history_size - 1) {
        char	**new_history;

        new_history = realloc(g_minishell->history, sizeof(char *) * (g_minishell->history_size + 1));
        if (!new_history)
            exit(1);
        ft_memset(new_history + g_minishell->history_index, 0, sizeof(char *));
        g_minishell->history[g_minishell->history_index] = line;
        g_minishell->history_index++;
    }
    else {
        g_minishell->history[g_minishell->history_index] = ft_strdup(line);
        if (g_minishell->history_size == 0)
            g_minishell->history_size++;
        free(g_minishell->history[g_minishell->history_index]);
        g_minishell->history[g_minishell->history_index] = line;
    }
}

char	*ft_get_history(int index) {
    if (index < 0 || index >= g_minishell->history_size)
        return NULL;
    else
        return ft_strdup(g_minishell->history[index]);
}
