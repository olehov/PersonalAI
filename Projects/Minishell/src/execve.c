#include "minishell.h"

int exec_builtin(char **args) {
    int i;

    if (ft_strcmp(args[0], "cd") == 0)
        return ft_cd(args, g_minishell->env);
    else if (ft_strcmp(args[0], "pwd") == 0)
        return ft_pwd(g_minishell->env);
    else if (ft_strcmp(args[0], "echo") == 0)
        return ft_echo(args, 1);
    else if (ft_strcmp(args[0], "export") == 0)
        return ft_export(args);
    else if (ft_strcmp(args[0], "unset") == 0)
        return ft_unset(args);
    else if (ft_strcmp(args[0], "env") == 0)
        print_env();
    else if (ft_strcmp(args[0], "exit") == 0) {
        if (args[1] != NULL && args[2] == NULL)
            exit(ft_atoi(args[1]));
        write(STDERR_FILENO, "minishell: exit: too many arguments\n", 34);
    }
    return -1;
}

int exec_external(char **path, char **args) {
    pid_t	pid;
    int		status;

    if ((pid = fork()) == 0) {
        if (execve(path[0], args, g_minishell->env) == -1)
            exit(1);
    }
    else {
        waitpid(pid, &status, 0);
        return WEXITSTATUS(status);
    }
}
