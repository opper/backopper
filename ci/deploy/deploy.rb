# config valid for current version and patch releases of Capistrano
lock '~> 3.10.0'

set :application, 'backopper'
set :repo_url, 'git@bitbucket.org:opper/backopper.git'

set :branch, 'master'

set :deploy_user, 'serverpilot'

set :deploy_to, "/opt/backups/#{fetch(:application)}"

append :linked_files, "src/secrets/__init__.py"

after "deploy:finished", "dependencies:install"