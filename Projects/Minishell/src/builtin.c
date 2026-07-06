#include "minishell.h"

int ft_cd(char **args, t_env *envp) {
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

int ft_echo(char **args, int i) {
    int j;

    if (args[i] == NULL)
        return 0;
    j = i + 1;
    while (args[j] != NULL) {
        if (j > i+1)
            write(STDOUT_FILENO, " ", 1);
        ft_putstr_fd(args[j], STDOUT_FILENO);
        j++;
    }
    if (!ft_strchr(args[i], 'n'))
        write(STDOUT_FILENO, "\n", 1);
    return 0;
}

int ft_export(char **args) {
    int i;

    if (args[1] == NULL)
        print_env();
    else
        while (*args != NULL) {
            export_one_var(args, g_minishell->env);
            args++;
        }
    return 0;
}

void	export_one_var(char **arg, t_env *envp) {
    char	**new_env;

    if (!ft_strchr(*arg, '='))
        add_to_env(arg[0], NULL);
    else {
        int i = 0;
        while (envp[i]) {
            if (ft_strcmp(envp[i]->name, arg[0]) == 0) {
                set_var_value(&g_minishell->env, envp[i], arg[1]);
                return ;
            }
            i++;
        }
        add_to_env(arg[0], arg[1]);
    }
}

int ft_unset(char **args) {
    int i;

    if (args[1] == NULL)
        print_env();
    else
        while (*args != NULL) {
            unset_one_var(args, g_minishell->env);
            args++;
        }
    return 0;
}

void	unset_one_var(char *arg, t_env *envp) {
    int i = 0;

    while (envp[i]) {
        if (ft_strcmp(envp[i]->name, arg) == 0)
            unset_and_free(&g_minishell->env, envp[i]);
        else
            i++;
    }
}

int ft_env(t_env *envp) {
    print_env();
    return 0;
}

int ft_exit(char **args) {
    if (args[1] != NULL && args[2] == NULL)
        exit(ft_atoi(args[1]));
    else if (args[1] != NULL && args[2] != NULL)
        write(STDERR_FILENO, "minishell: exit: too many arguments\n", 34);
    else
        exit(0);
    return -1;
}
