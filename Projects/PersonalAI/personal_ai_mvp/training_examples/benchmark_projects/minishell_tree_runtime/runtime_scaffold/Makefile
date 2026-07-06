# Makefile for the minishell runtime

# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -Werror -g

# Source files
SRCS = main.c shell.c parser/lexer.c parser/parser.c executor/exec.c executor/redirections.c executor/pipes.c builtins/builtins.c signals/interactive.c

# Object files
OBJS = $(SRCS:.c=.o)

# Executable name
TARGET = minishell

# Default target
all: $(TARGET)

# Create the executable
$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS)

# Compile source files into object files
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean up object files and executables
clean:
	rm -f $(OBJS) $(TARGET)