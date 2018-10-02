server '', roles: %w{dist}, user: fetch(:deploy_user), port: 222

# login to remote server is done via ssh-key authentication
# never, ever with password
set :ssh_options, {
    keys: %w(/var/lib/jenkins/.ssh/id_rsa),
    auth_methods: %w(publickey)
}