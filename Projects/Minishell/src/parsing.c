#include "minishell.h"

int parse_redirections(char **args) {
    int i;

    i = 0;
    while (args[i] != NULL && ft_strncmp(args[i], "<<", 2) == 0)
        i++;
    if (i > 0 && args[i])
        return -1; // Error: redirection not at the end
    else {
        int j;

        for (j = 0; j < i; j++)
            free(args[j]);
        char **new_args;
        new_args = malloc((g_minishell->cmd_count + 1) * sizeof(char *));
        if (!new_args)
            exit(1);
        ft_memset(new_args, 0, (g_minishell->cmd_count + 1) * sizeof(char *));
        int k;

        for (k = i; k < g_minishell->cmd_count - 1; k++)
            new_args[k] = args[k+1];
        return i;
    }
}

int parse_redirections(char **args, int index) {
    while (index > 0 && ft_strncmp(args[index], "<<", 2) == 0)
        index--;
    if (index < 0 || !ft_strcmp(args[0], "echo") || !ft_strcmp(args[0], "cd") || !ft_strcmp(args[0], "pwd") || !ft_strcmp(args[0], "export") || !ft_strcmp(args[0], "unset") || !ft_strcmp(args[0], "env") || !ft_strcmp(args[0], "exit"))
        return -1; // Error: invalid command
    else {
        int i;

        for (i = index + 1; args[i]; i++) {
            if (!ft_strncmp(args[i], "<<", 2) == 0 && ft_strlen(args[i]) > 2)
                break;
            else if (args[i][0] == '>' || args[i][0] == '<') {
                char *redir_type = NULL;
                int j;

                for (j = i; args[j]; j++) {
                    while (args[j][k]) {
                        k++;
                        g_minishell->cmd_count++;
                    }
                }
            }
        }
    }
}

int parse_redirections(char **args) {
    int i;

    i = 0;
    while (args[i] != NULL && ft_strncmp(args[i], "<<", 2) == 0)
        i++;
    if (i > 0 && args[i])
        return -1; // Error: redirection not at the end
    else {
        int j;

        for (j = 0; j < g_minishell->cmd_count; j++)
            free(args[j]);
        char **new_args;
        new_args = malloc((g_minishell->history_size + i) * sizeof(char *));
        if (!new_args)
            exit(1);
        ft_memset(new_args, 0, (g_minishell->history_size + i) * sizeof(char *));
        int k;

        for (k = 0; k < g_minishell->cmd_count - 1; k++)
            new_args[k] = args[g_minishell->start];
    }
}

int parse_redirections(char **args, int index) {
    while (index > 0 && ft_strncmp(args[index], "<<", 2) == 0)
        index--;
    if (index < 0 || !ft_strcmp(args[0], "echo") || !ft_strcmp(args[0], "cd") || !ft_strcmp(args[0], "pwd") || !ft_strcmp(args[0], "export") || !ft_strcmp(args[0], "unset") || !ft_strcmp(args[0], "env") || !ft_strcmp(args[0], "exit"))
        return 1;
    else {
        int i;

        for (i = index; args[i] != NULL && ft_strnstr(args[i], "|", 1) == 0; i++)
            ;
        if (!args[i]) {
            write(STDERR_FILENO, "minishell: command not found\n", 28);
            return -1;
        }
        else {
            char **new_args;
            int j;

            new_args = malloc((i + 1) * sizeof(char *));
            ft_memset(new_args, 0, (g_minishell->cmd_count + i) * sizeof(char *));
            for (j = 0; j < i; j++)
                new_args[j] = args[j];
            return i;
        }
    }
}

int parse_redirections(char **args) {
    int i;

    while (args[i]) {
        if (!ft_strcmp(args[i], "<<") || !ft_strcmp(args[i], ">>"))
            g_minishell->exit_status = 1;
        else
            break;
    }

    char	**new_args;
    new_args = malloc((g_minishell->cmd_count + i) * sizeof(char *));
    if (!new_args)
        exit(1);
    ft_memset(new_args, 0, (g_minishell->cmd_count + i) * sizeof(char *));
    int j;

    for (j = 0; args[j]; j++) {
        char *quote_start, *quote_end;
        quote_start = ft_strrchr(args[j], '"');
        if (!quote_start)
            quote_start = ft_strrchr(args[j], '\'');
        else
            quote_end = ft_strnstr(args[j] + (quote_start - args[j]), " ", 1);
        if (!quote_end) {
            write(STDERR_FILENO, "minishell: unclosed quotation\n", 32);
            exit(1);
        }
    }

    char	**split_args(char *line) {
        int i;
        for (i = 0; line[i]; i++) {
            while (line[i] && !(ft_isspace(line[i]) || line[i] == '|' || line[i] == '>' || line[i] == '<'))
                i++;
            if (i > 0) {
                args[g_minishell->cmd_count] = ft_strdup_until(line, g_minishell->start);
                g_minishell->start = i + 1;
                g_minishell->cmd_count++;
            }
        }
    }

    char	**split_args(char *line) {
        int k;

        for (k = 0; args[k]; k++) {
            if (!ft_strcmp(args[k], "<<") || !ft_strcmp(args[k], ">>"))
                continue;
            else
                break;
        }

        while (args[i]) {
            char **tokenized_args;
            tokenized_args = split_token(g_minishell->exit_status, line);
            int i;

            for (i = 0; tokenized_args[i]; i++) {
                if (!ft_strcmp(tokenized_args[i], "<<") || !ft_strcmp(tokenized_args[i], ">>"))
                    g_minishell->exit_status = -1;
                else
                    break;
            }

    }
