# Adding git (or hg, or svn) dependencies in setup.py (Python)
https://mike.zwobble.org/2013/05/adding-git-or-hg-or-svn-dependencies-in-setup-py/

example: `git+ssh://git@github.com/yoyonel/twint.git@develop#egg=twint`
- `git+ssh://`: protocol
- `git@github.com/yoyonel/twint.git`: git remote
- `@develop`: branch or commit
- `#egg=twint`: python package egg name
