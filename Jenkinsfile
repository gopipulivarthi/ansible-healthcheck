pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        PATH = "/opt/healthcheck/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        REPORT_PUBLISH_DIR = "/var/lib/healthcheck/reports"
        // Replace these two values with your Gmail address and report recipient.
        GMAIL_USER = "YOUR_GMAIL_ADDRESS@gmail.com"
        REPORT_EMAIL_TO = "RECIPIENT_ADDRESS@gmail.com"
    }

    stages {
        stage('Install Ansible collections') {
            steps {
                sh 'ansible-galaxy collection install -r collections/requirements.yml'
            }
        }

        stage('Validate inventory') {
            steps {
                sh 'ansible-inventory --graph'
            }
        }

        stage('Run server health checks') {
            steps {
                withCredentials([string(credentialsId: 'ansible-vault-password', variable: 'ANSIBLE_VAULT_PASSWORD')]) {
                    sh '''#!/usr/bin/env bash
                        set -euo pipefail
                        set +x
                        umask 077
                        trap 'rm -f .vault-pass' EXIT
                        printf '%s' "$ANSIBLE_VAULT_PASSWORD" > .vault-pass
                        mkdir -p reports
                        ansible-playbook -i inventory/hosts.ini playbooks/healthcheck.yml \\
                          --vault-password-file .vault-pass \\
                          -e "run_id=build-${BUILD_NUMBER}"
                        mkdir -p "$REPORT_PUBLISH_DIR"
                        cp -a reports/. "$REPORT_PUBLISH_DIR/"
                    '''
                }
            }
        }

        stage('Email report to Gmail') {
            steps {
                withCredentials([string(credentialsId: 'gmail-app-password', variable: 'GMAIL_APP_PASSWORD')]) {
                    sh '''#!/usr/bin/env bash
                        set -euo pipefail
                        set +x
                        python scripts/send_report.py \\
                          --report-dir "$REPORT_PUBLISH_DIR" \\
                          --run-id "build-${BUILD_NUMBER}"
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**/*.json', allowEmptyArchive: true
        }
    }
}
