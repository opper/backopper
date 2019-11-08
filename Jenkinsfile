pipeline {
    agent any
    stages {
        stage ('install deps') {
            steps {
                sh 'dep ensure'
            }
        }

        stage ('build backopper') {
            steps {
                sh 'go build .'
            }
        }
    }
}
