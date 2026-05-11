pipeline {
    agent any

    environment {
        IMAGE_NAME = "nestjs-backend"
        CONTAINER_NAME = "nestjs-app"
    }

    stages {

        stage('Install Dependencies') {
            steps {
                sh 'npm install'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'npm run test'
            }
        }

        stage('Build App') {
            steps {
                sh 'npm run build'
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build -t ${IMAGE_NAME} .'
            }
        }

        stage('Trivy Scan') {
            steps {

                sh '''
                trivy image \
                --severity HIGH,CRITICAL \
                --ignore-unfixed \
                ${IMAGE_NAME} > trivy-report.txt
                '''

                script {

                    def report = readFile('trivy-report.txt')

                    if (report.contains("HIGH:") || report.contains("CRITICAL:")) {

                        withCredentials([
                            string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                            string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
                        ]) {

                            sh """
                            curl -s -X POST https://api.telegram.org/bot${BOT_TOKEN}/sendMessage \
                            -d chat_id=${CHAT_ID} \
                            --data-urlencode text='⚠️ Trivy Vulnerabilities Detected

Job: ${JOB_NAME}
Build: #${BUILD_NUMBER}

${report}'
                            """
                        }
                    }
                }
            }
        }

        stage('Deploy Container') {
            steps {

                sh '''
                docker rm -f ${CONTAINER_NAME} || true

                docker run -d \
                --name ${CONTAINER_NAME} \
                -p 3000:3000 \
                ${IMAGE_NAME}
                '''
            }
        }
    }

    post {

        success {

            withCredentials([
                string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
            ]) {

                sh '''
                curl -s -X POST https://api.telegram.org/bot${BOT_TOKEN}/sendMessage \
                -d chat_id=${CHAT_ID} \
                -d text="✅ SUCCESS: ${JOB_NAME} #${BUILD_NUMBER}"
                '''
            }
        }

        failure {

            withCredentials([
                string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
            ]) {

                sh '''
                curl -s -X POST https://api.telegram.org/bot${BOT_TOKEN}/sendMessage \
                -d chat_id=${CHAT_ID} \
                -d text="❌ FAILED: ${JOB_NAME} #${BUILD_NUMBER}"
                '''
            }
        }
    }
}