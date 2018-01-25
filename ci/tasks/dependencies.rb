namespace :dependencies do
    task :install do
        on roles(:app) do
            execute "cd #{current_path} && virtualenv venv && source venv/bin/activate && pip install ."
        end
    end
end