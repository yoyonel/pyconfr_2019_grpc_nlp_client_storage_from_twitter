# PyConFR 2019 - GRPC NLP

## Instructions

Structure is based on [this article](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure). Source code can be found in the `src` folder, and tests in the `tests` folder.

### Installation

To install the package (development mode):

```bash
➤ make pip-install
```

### Tests

#### Tox
~~We use `tox` for the tests. This ensure a clear separation between the development environment and the test environment.
To launch the tests, run the `tox` command:~~

~~It first starts with a bunch of checks (`flask8` and others) and then launch the tests using python 3.~~

#### Pytest
You can use `pytest` for the tests:
```bash
➤ make pytest           
pytest -v
```
