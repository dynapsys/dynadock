# Contributing to DynaDock

First off, thank you for considering contributing to DynaDock! It's people like you that make DynaDock such a great tool.

## Where do I go from here?

If you've noticed a bug or have a question, [search the issue tracker](https://github.com/dynapsys/dynadock/issues) to see if someone else has already reported the issue. If not, feel free to [open a new issue](https://github.com/dynapsys/dynadock/issues/new).

## Fork & create a branch

If you want to contribute with code, please fork the repository and create a new branch. This is where you'll be working on your changes.

```bash
git checkout -b my-new-feature
```

## Code Style

Please follow the coding style of the project. We use `black` for formatting and `ruff` for linting. You can run the following command to format your code:

```bash
make format
```

And to check for linting errors:

```bash
make lint
```

## Submitting a pull request

When you're ready to submit a pull request, please make sure your code is well-tested and that all tests are passing.

```bash
make test
```

After that, you can open a new pull request and we'll review it as soon as possible.
