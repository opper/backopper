namespace :dependencies do
    task :install do
        on roles(:dist) do
            execute "cd #{current_path} && virtualenv --python=/usr/bin/python3.5 venv && source venv/bin/activate && python setup.py bdist_wheel --universal"
            execute "mv #{current_path}/dist/* #{fetch(:dist_path)}/backopper"
        end
    end
end