#!/bin/sh

echo "$VAULT_PASS" > vault_pass.txt
ansible-vault decrypt --vault-password-file vault_pass.txt deploy/deploy_ssh_key
chmod 0600 deploy/deploy_ssh_key
ansible-playbook --check --vault-password-file vault_pass.txt --private-key deploy/deploy_ssh_key -i deploy/hosts deploy/deploy.yaml
