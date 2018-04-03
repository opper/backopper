namespace :dependencies do
    task :install do
        on roles(:dist) do
            execute "cd #{current_path} && virtualenv --python=/usr/bin/python3.6 venv && source venv/bin/activate && python setup.py bdist_wheel --universal --rotate 5"
            execute "mv #{current_path}/dist/* #{fetch(:dist_path)}"
        end
    end
end