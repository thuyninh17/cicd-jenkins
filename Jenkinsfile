pipeline {
    agent any

    environment {
        IMAGE_NAME = "nestjs-backend"
        CONTAINER_NAME = "nestjs-app"
        SONAR_PROJECT_KEY = "nestjs-backend"
        SONAR_HOST_URL = "http://192.168.234.133:9000"
        SONAR_TOKEN = credentials('sonar-token')
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

        // =========================
        // SONAR SCAN
        // =========================
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        sonar-scanner \
                            -Dsonar.projectKey=$SONAR_PROJECT_KEY \
                            -Dsonar.projectName=$SONAR_PROJECT_KEY \
                            -Dsonar.sources=. \
                            -Dsonar.host.url=$SONAR_HOST_URL \
                            -Dsonar.login=$SONAR_TOKEN
                    '''
                }
            }
        }

        // =========================
        // QUALITY GATE (CAPTURE STATUS)
        // =========================
        stage('Quality Gate') {
            steps {
                timeout(time: 55, unit: 'MINUTES') {
                    script {
                        def qg = waitForQualityGate()
                        env.SONAR_STATUS = qg.status

                        echo "SonarQube Status: ${qg.status}"

                        if (qg.status != 'OK') {
                            echo "WARNING: SonarQube quality gate is ${qg.status}. Pipeline will continue."
                        }
                    }
                }
            }
        }

        // =========================
        // SONAR TELEGRAM NOTIFY
        // =========================
        stage('Sonar Notification') {
            steps {
                script {
                    withCredentials([
                        string(credentialsId: 'telegram-bot-token', variable: 'BOT_TOKEN'),
                        string(credentialsId: 'telegram-chat-id', variable: 'CHAT_ID')
                    ]) {
                        sh """
                            python3 scripts/sonar_notify.py \
                                --sonar-host "${SONAR_HOST_URL}" \
                                --project-key "${SONAR_PROJECT_KEY}" \
                                --sonar-token "${SONAR_TOKEN}" \
                                --quality-gate "${SONAR_STATUS}" \
                                --bot-token "$BOT_TOKEN" \
                                --chat-id "$CHAT_ID" \
                                --job-name "${JOB_NAME}" \
                                --build-number "${BUILD_NUMBER}" \
                                --build-url "${BUILD_URL}" \
                                --branch-name "${BRANCH_NAME}"
                        """
                    }
                }
            }
        }

        // =========================
        // DOCKER BUILD
        // =========================
        stage('Docker Build') {
            steps {
                sh 'docker build -t ${IMAGE_NAME} .'
            }
        }

        // =========================
        // TRIVY SCAN
        // =========================
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
                            echo "WARNING: Trivy found HIGH/CRITICAL vulnerabilities. Pipeline will continue."
                        } else if (rc != 0) {
                            error("Trivy notification failed: " + rc)
                        }
                    }
                }
            }
        }

        // =========================
        // DEPLOY
        // =========================
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

    // =========================
    // FINAL NOTIFICATIONS
    // =========================
    post {

        success {
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
                        --text "⚠️ UNSTABLE: ${JOB_NAME} #${BUILD_NUMBER}" \
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