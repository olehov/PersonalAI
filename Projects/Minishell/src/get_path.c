#include "minishell.h"

char	**get_paths(char **path_env) {
    int i;
    char	**paths;

    paths = malloc(sizeof(char *));
    if (!paths)
        exit(1);
    *paths = NULL;
    i = 0;
    while (path_env[i]) {
        if (ft_strnstr(path_env[i], PATH_SEP, ft_strlen(path_env[i])))
            break ;
        else
            i++;
    }
    return (split_path(path_env + i));
}

char	**get_cmd(char *line) {
    char	**args;
    int		i;

    args = malloc((1024) * sizeof(char *));
    if (!args)
        exit(1);
    ft_memset(args, 0, 1024 * sizeof(char *));
    i = 0;
    while (*line && (i < 1023)) {
        if (*line == '"' || *line == '\'') {
            skip_quotes(line + 1, args[i]);
            line += ft_strlen(*args) ? ft_strlen(args[i]) : 1; // If the string is empty, increment by one to avoid infinite loop
            i++;
        }
        else {
            while (*line && *line != ' ' && *line != '\n' && *line != '|' && *line != '>' && *line != '<')
                line++;
            if (i < 1023) {
                args[i] = ft_strdup_until(line, i);
                i++;
            }
        }
    }
    return (args);
}

char	**split_path(char **path_env) {
    char	**paths;
    int		i;

    paths = malloc((1024) * sizeof(char *));
    if (!paths)
        exit(1);
    ft_memset(paths, 0, 1024 * sizeof(char *));
    i = 0;
    while (*path_env && (i < 1023)) {
        char	*path;

        path = ft_strtrim(*path_env, "/");
        if (!ft_strcmp(path, ""))
            continue ;
        paths[i] = path;
        i++;
        path_env++;
    }
    return (paths);
}

void skip_quotes(char *str, char **arg) {
    int j;
    int in_quote;

    arg[0] = ft_strdup("");
    while (*str && *(arg + 0)) {
        if (!in_quote && *str == '"' || !in_quote && *str == '\'') {
            in_quote = 1 - in_quote; // Toggle the quote flag
            str++;
            continue ;
        }
        else if (in_quote) {
            arg[0] = ft_strjoin_free(arg[0], str, 3);
            while (*str)
                str++;
            break ;
        }
        else
            *(arg + j++) = *str;
    }
}

char	*ft_strdup_until(char *line, int i) {
    char	*start;

    start = line;
    if (i == -1 || !ft_strchr(line, '/'))
        return ft_strdup(start);
    while (*line && *line != '/')
        line++;
    return ft_strdup(start);
}
