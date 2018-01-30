server '192.81.221.208', roles: %w{app}, user: fetch(:deploy_user), port: 25642 # opper-staging
# server '188.166.13.154', roles: %w{app}, user: fetch(:deploy_user), port: 222 # opper-acceptance
# server '188.166.77.230', user: 'deploy', roles: %w{app} # opper-live

set :ssh_options, {
    keys: %w(/var/lib/jenkins/.ssh/id_rsa),
    auth_methods: %w(publickey)
}
