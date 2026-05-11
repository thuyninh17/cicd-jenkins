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
                        --scanners vuln \
                        --severity HIGH,CRITICAL \
                        --ignore-unfixed \
                        --format json \
                        -o trivy-report.json \
                        ${IMAGE_NAME} 2>/dev/null || true

                    trivy image \
                        --scanners vuln \
                        --severity HIGH,CRITICAL \
                        --ignore-unfixed \
                        ${IMAGE_NAME} > trivy-report.txt 2>&1 || true
                '''

                withCredentials([
                    string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                    string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
                ]) {
                    script {
                        def rc = sh(
                            returnStatus: true,
                            script: '''
                                python3 scripts/trivy_notify.py \
                                    --report trivy-report.txt \
                                    --report-json trivy-report.json \
                                    --bot-token $BOT_TOKEN \
                                    --chat-id $CHAT_ID \
                                    --job-name "${JOB_NAME}" \
                                    --build-number "${BUILD_NUMBER}" \
                                    --image "${IMAGE_NAME}"
                            '''
                        )

                        if (rc == 2) {
                            env.TRIVY_FAILED = "1"
                            currentBuild.result = 'UNSTABLE'
                            echo "Trivy found HIGH/CRITICAL vulnerabilities. Marking build UNSTABLE and continuing."
                        } else if (rc != 0) {
                            error("Trivy notification step failed (unexpected exit code: " + rc + ").")
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
            script {
                if (env.TRIVY_FAILED != "1") {
                    withCredentials([
                        string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                        string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
                    ]) {
                        sh '''
                            python3 scripts/notify.py \
                                --bot-token $BOT_TOKEN \
                                --chat-id $CHAT_ID \
                                --status success \
                                --job-name "${JOB_NAME}" \
                                --build-number "${BUILD_NUMBER}"
                        '''
                    }
                } else {
                    echo "Skipping success Telegram notification due to Trivy failure."
                }
            }
        }

        unstable {
            withCredentials([
                string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
            ]) {
                sh '''
                    python3 scripts/notify.py \
                        --bot-token $BOT_TOKEN \
                        --chat-id $CHAT_ID \
                        --status failure \
                        --text "⚠️ UNSTABLE (Trivy): ${JOB_NAME} #${BUILD_NUMBER} (deployed for further testing)" \
                        --job-name "${JOB_NAME}" \
                        --build-number "${BUILD_NUMBER}"
                '''
            }
        }

        failure {
            withCredentials([
                string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
            ]) {
                sh '''
                    python3 scripts/notify.py \
                        --bot-token $BOT_TOKEN \
                        --chat-id $CHAT_ID \
                        --status failure \
                        --text "❌ FAILED: ${JOB_NAME} #${BUILD_NUMBER}" \
                        --job-name "${JOB_NAME}" \
                        --build-number "${BUILD_NUMBER}"
                '''
            }
        }
    }
}