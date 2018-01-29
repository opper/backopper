namespace :dependencies do
    task :install do
        on roles(:app) do
            execute "cd #{current_path} && virtualenv --python=/usr/bin/python3.6 venv && source venv/bin/activate && pip install ."
        end
    end
end