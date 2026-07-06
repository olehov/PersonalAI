# Coding Style

## General Principles

1. Correctness first
2. Readability second
3. Performance third
4. Optimization only when justified by measurements

---

## Code Quality

Prefer:

- self-documenting code
- meaningful names
- small functions
- clear interfaces
- explicit behavior

Avoid:

- premature optimization
- unnecessary abstractions
- overengineering
- hidden side effects

---

## Modern C++

### Preferred Standard

C++23

### Preferred Features

- std::ranges
- std::span
- std::optional
- std::variant
- concepts
- constexpr
- smart pointers
- RAII

### Avoid

- raw owning pointers
- unnecessary dynamic allocation
- legacy C APIs when modern alternatives exist

---

## Python

Prefer:

- type hints
- dataclasses
- pathlib
- virtual environments

---

## Java

Prefer:

- modern Java features
- records
- streams when appropriate

Avoid:

- unnecessary inheritance

---

## Problem Solving

Preferred order:

1. Working solution
2. Clean solution
3. Optimized solution

---

## Architecture

Prefer:

- composition over inheritance
- modular design
- testability
- maintainability

---

## Learning

When new patterns repeatedly appear:

- create notes
- extract reusable knowledge
- update existing documentation