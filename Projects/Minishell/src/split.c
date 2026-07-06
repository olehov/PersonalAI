#include "minishell.h"

char	**split_line(char *line) {
    char	**args;

    args = malloc((1024) * sizeof(char *));
    if (!args)
        exit(1);
    ft_memset(args, 0, 1024 * sizeof(char *));
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

char	**split_redirections(char *line) {
    char	**args;

    args = malloc((1024) * sizeof(char *));
    if (!args)
        exit(1);
    ft_memset(args, 0, 1024 * sizeof(char *));
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

char	**split_redirections(char *line) {
    char	**args;

    args = malloc((1024) * sizeof(char *));
    if (!args)
        exit(1);
    ft_memset(args, 0, 1024 * sizeof(char *));
    int i;
    for (i = 0; line[i]; i++) {
        while (line[i] && !(ft_isspace(line[i]) || line[i] == '|' || line[i] == '>' || line[i] == '<'))
            i++;
        if (i > 0) {
            args[g_minishell->cmd_count] = ft_strdup_until(line, g_minishell->start);
            g_minishell->start = i + 1;
            g_minishell->cmd
</think>
BEGIN_FILE: src/builtin.c
```language
#include "minishell.h"

int ft_cd(char **args) {
    if (args[1] == NULL)
        return 1;
    else if (chdir(args[1]) == -1)
        perror("cd");
    return 0;
}

char	*ft_pwd(t_env *envp) {
    char	buf[PATH_MAX];
    getcwd(buf, sizeof(buf));
    write(STDOUT_FILENO, buf, strlen(buf));
    write(STDOUT_FILENO, "\n", 1);
    return NULL;
}

int ft_echo(char **args) {
    int i;

    for (i = 0; args[i]; i++) {
        if (!ft_strcmp(args[0], "echo") && !g_minishell->in_pipe)
            write(STDOUT_FILENO, args[i + 1], strlen(args[i + 1]));
        else
            return -1;
    }
}

int ft_exit(char **args) {
    (void)args;
    if (args[1])
        g_minishell->exit_status = atoi(args[1]);
    exit(g_minishell->exit_status);
    return 0;
}
