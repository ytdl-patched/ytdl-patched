#!/bin/bash
cat << EOF > .git/hooks/pre-commit
#!/bin/bash
set -xe
npx lint-staged
make clean
EOF
chmod a+x .git/hooks/pre-commit
