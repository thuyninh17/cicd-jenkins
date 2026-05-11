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
                        ${IMAGE_NAME} > trivy-report.txt 2>&1
                '''

                script {
                    def reportContent = readFile('trivy-report.txt').trim()

                    // Đếm số CVE HIGH và CRITICAL
                    def highCount = sh(
                        script: "grep -c ' HIGH ' trivy-report.txt || true",
                        returnStdout: true
                    ).trim()

                    def criticalCount = sh(
                        script: "grep -c ' CRITICAL ' trivy-report.txt || true",
                        returnStdout: true
                    ).trim()

                    def hasVulns = sh(
                        script: "grep -qE 'HIGH|CRITICAL' trivy-report.txt && echo 'yes' || echo 'no'",
                        returnStdout: true
                    ).trim()

                    if (hasVulns == 'yes') {
                        // Tạo summary message
                        writeFile file: 'telegram-summary.txt', text: """\
⚠️ Trivy Vulnerabilities Detected

Job: ${JOB_NAME}
Build: #${BUILD_NUMBER}
Image: ${IMAGE_NAME}

Total: HIGH=${highCount}, CRITICAL=${criticalCount}

📎 Full CVE report attached below.
"""
                        withCredentials([
                            string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                            string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
                        ]) {
                            // Gửi summary message
                            sh '''
                                curl -s -X POST \
                                    https://api.telegram.org/bot$BOT_TOKEN/sendMessage \
                                    -d chat_id=$CHAT_ID \
                                    --data-urlencode text@telegram-summary.txt
                            '''

                            // Gửi full report dưới dạng file đính kèm
                            sh '''
                                curl -s -X POST \
                                    https://api.telegram.org/bot$BOT_TOKEN/sendDocument \
                                    -F chat_id=$CHAT_ID \
                                    -F document=@trivy-report.txt \
                                    -F caption="Full Trivy Report - ${JOB_NAME} #${BUILD_NUMBER}"
                            '''
                        }
                    } else {
                        echo "No HIGH/CRITICAL vulnerabilities found."
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
                    curl -s -X POST \
                        https://api.telegram.org/bot$BOT_TOKEN/sendMessage \
                        -d chat_id=$CHAT_ID \
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
                    curl -s -X POST \
                        https://api.telegram.org/bot$BOT_TOKEN/sendMessage \
                        -d chat_id=$CHAT_ID \
                        -d text="❌ FAILED: ${JOB_NAME} #${BUILD_NUMBER}"
                '''
            }
        }
    }
}