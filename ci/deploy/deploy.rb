# config valid for current version and patch releases of Capistrano
lock '~> 3.10.0'

set :application, 'backopper'
set :repo_url, 'git@bitbucket.org:opper/backopper.git'

set :branch, 'master'

append :linked_files, "src/secrets/__init__.py"

set :deploy_to, '/opt/backopper'

set :dist_path, '/var/www/html/pip/backopper'

set :deploy_user, 'root'

after "deploy:finished", "dependencies:install"