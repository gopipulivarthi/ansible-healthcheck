# Automated Infrastructure Health Check & Monitoring Dashboard

A local DevOps lab that provisions VirtualBox VMs, runs cross-platform Ansible checks from Jenkins, stores JSON reports, displays them in a Flask dashboard, and emails each run through Gmail SMTP.

## 1. Lab layout

| VM | OS | IP | RAM | vCPU | Role |
|---|---|---:|---:|---:|---|
| controller | Ubuntu Server 24.04 | 192.168.56.10 | 4 GB | 2 | Jenkins, Ansible, Flask dashboard |
| linux01 | Ubuntu Server 24.04 | 192.168.56.21 | 1 GB | 1 | Linux managed node |
| win01 | Windows Server 2022 | 192.168.56.22 | 4 GB | 2 | Windows managed node |

Total VM memory: 9 GB. This leaves around 7 GB for the Windows host and VirtualBox. Close memory-heavy applications while all VMs are running.

All VMs use a VirtualBox host-only network. Do not bridge the dashboard or Jenkins ports to a public network.

## 2. Host prerequisites (Windows laptop)

You already have VirtualBox, Vagrant and Git installed. Check them in PowerShell:

```powershell
VBoxManage --version
vagrant --version
git --version
terraform version
```

Install Terraform if it is missing:

```powershell
winget install Hashicorp.Terraform
```

Close and reopen PowerShell, then check `terraform version`.

Check VirtualBox and Vagrant compatibility against the installed versions. Vagrant's VirtualBox provider supports VirtualBox 7.0, 7.1 and 7.2.

## 3. Create the GitHub repository

1. Create an empty GitHub repository named `ansible-healthcheck`.
2. Do not initialize it with a README, because this project already contains one.
3. Extract this project ZIP to `C:\DevOps\ansible-healthcheck` (or another short path).
4. Open PowerShell in that folder and run:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial infrastructure health check project"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/ansible-healthcheck.git
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME`. Authenticate to GitHub using the supported browser prompt or Git Credential Manager. Never put a personal access token in the repository or a script.

## 4. Provision VirtualBox VMs through Terraform + Vagrant

From the project root in PowerShell:

```powershell
cd C:\DevOps\ansible-healthcheck
cd terraform
terraform init
terraform validate
terraform plan
terraform apply
```

Type `yes` when Terraform asks for confirmation. Terraform invokes `vagrant up --provider=virtualbox` from the project root. Vagrant creates and configures the three VMs.

Useful Vagrant commands (run from the project root, not the terraform folder):

```powershell
vagrant status
vagrant up
vagrant halt
vagrant resume
vagrant ssh controller
vagrant ssh linux01
vagrant destroy -f
```

To destroy the lab through Terraform, run `terraform destroy` from the `terraform` folder. Do not run `vagrant destroy` and `terraform destroy` at the same time.

**Terraform design note:** this VirtualBox lab uses Terraform's built-in `terraform_data` resource to call Vagrant. Vagrant is the VM lifecycle/provider layer. This avoids depending on an unofficial VirtualBox Terraform provider. Terraform is orchestrating Vagrant rather than independently managing VirtualBox VM objects.

## 5. First-time Windows box download note

The Vagrantfile pins `gusztavvargadr/windows-server-2022-standard` version `2607.0.0`, which provides a VirtualBox build. The current publisher box is served through HCP Vagrant; its service is scheduled to end on 31 December 2026. Download/cache the box while it is available:

```powershell
vagrant box add gusztavvargadr/windows-server-2022-standard --provider virtualbox --box-version 2607.0.0
vagrant box list
```

If the box is already cached, Vagrant can use that local copy. If the publisher migrates the box after the service retirement, update the box source/version in `Vagrantfile` to the publisher's new location.

## 6. Verify VMs and access the control node

```powershell
vagrant status
vagrant ssh controller
```

On the controller VM:

```bash
java -version
sudo systemctl status jenkins --no-pager
/opt/healthcheck/venv/bin/ansible --version
ip -br address
```

Jenkins URL: `http://192.168.56.10:8080`

Get the initial Jenkins password:

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Complete the Jenkins wizard, install suggested plugins, create your first admin user, and install/verify these plugins under **Manage Jenkins → Plugins**:

- Git plugin
- Pipeline plugin
- Credentials Binding plugin

The Jenkins package is installed with Java 21. Keep Jenkins and Java patched.

## 7. Clone your GitHub project onto the controller

From the controller VM, switch to the Vagrant user and clone your repository:

```bash
sudo -iu vagrant
git clone https://github.com/YOUR_GITHUB_USERNAME/ansible-healthcheck.git
cd ansible-healthcheck
```

For a private GitHub repository, configure an SSH deploy key or a credential helper. Do not embed a GitHub token in the repository URL or Jenkinsfile.

## 8. Create and encrypt Ansible credentials

The two Vagrant managed nodes use the lab-only account `vagrant` with password `vagrant`. This is for an isolated host-only training lab only; never reuse it in production.

From the cloned project directory on the controller:

```bash
./scripts/create-vault.sh
```

Enter a new Ansible Vault password when prompted. This encrypts `group_vars/all/vault.yml`. Commit and push the **encrypted** file so Jenkins can check it out:

```bash
git add group_vars/all/vault.yml
git commit -m "Add encrypted Ansible lab credentials"
git push
```

Keep the vault password separately; Jenkins will need it as a secret credential. Do not share or commit the vault password.

If you change either Vagrant node's login password, update the values in the vault file before encrypting it.

## 9. Test Ansible connectivity manually

On the controller, still inside the cloned repository:

```bash
/opt/healthcheck/venv/bin/ansible-galaxy collection install -r collections/requirements.yml
```

Create a temporary vault-password file (replace the example value with the vault password you selected):

```bash
printf '%s' 'YOUR_VAULT_PASSWORD' > .vault-pass
chmod 600 .vault-pass
```

Test Linux:

```bash
/opt/healthcheck/venv/bin/ansible linux -m ansible.builtin.ping --vault-password-file .vault-pass
```

Test Windows:

```bash
/opt/healthcheck/venv/bin/ansible win01 -m ansible.windows.win_ping --vault-password-file .vault-pass
```

Run the full playbook:

```bash
/opt/healthcheck/venv/bin/ansible-playbook -i inventory/hosts.ini playbooks/healthcheck.yml --vault-password-file .vault-pass -e run_id=manual-1
```

Inspect reports:

```bash
find reports -type f -maxdepth 3 -print
cat reports/manual-1/linux01.json
cat reports/manual-1/win01.json
rm -f .vault-pass
```

If Windows connectivity fails, confirm the VM is up, that the box has WinRM enabled, and that the controller can reach `192.168.56.22:5985`. Ansible uses NTLM over the isolated host-only network in this lab. Do not expose WinRM to the internet.

## 10. Install and start the Flask dashboard

From the cloned repository on the controller:

```bash
sudo ./scripts/install-dashboard.sh
sudo systemctl status healthcheck-dashboard --no-pager
```

Open this URL in your Windows browser:

`http://192.168.56.10:5000`

The dashboard reads published reports from `/var/lib/healthcheck/reports`. It refreshes every 60 seconds and shows the newest run plus recent run history.

Useful commands:

```bash
sudo journalctl -u healthcheck-dashboard -f
sudo systemctl restart healthcheck-dashboard
```

## 11. Configure Gmail App Password

1. Sign in to the Gmail account that will send the reports.
2. Enable 2-Step Verification on the Google account.
3. Create an App Password for this lab (if Google makes the option available for the account).
4. Copy the generated App Password. Do not use your normal Gmail password.

In Jenkins, open **Manage Jenkins → Credentials → System → Global credentials → Add Credentials** and create:

| Kind | ID | Secret |
|---|---|---|
| Secret text | `ansible-vault-password` | The Ansible Vault password from step 8 |
| Secret text | `gmail-app-password` | The Gmail App Password |

The Gmail sender and destination addresses are configured in the `environment` section of `Jenkinsfile`. Replace `YOUR_GMAIL_ADDRESS@gmail.com` and `RECIPIENT_ADDRESS@gmail.com`, then commit and push the change.

## 12. Create the Jenkins pipeline job

1. Open `http://192.168.56.10:8080`.
2. Select **New Item**.
3. Enter `healthcheck-dashboard` as the item name.
4. Select **Pipeline** and click OK.
5. Under **Pipeline**, select **Pipeline script from SCM**.
6. SCM: **Git**; enter your GitHub repository URL.
7. Add a GitHub credential if the repository is private.
8. Branch specifier: `*/main`.
9. Script path: `Jenkinsfile`.
10. Save and click **Build Now**.

The job installs the Ansible collection, validates the inventory, runs the Windows/Linux checks, publishes reports to `/var/lib/healthcheck/reports`, emails the summary and JSON attachments, and archives JSON reports in Jenkins.

If the pipeline reports `credentials ... not found`, check the two credential IDs exactly. If `sh: not found` appears, ensure the agent is the Ubuntu controller and uses the default Jenkins Unix executor.

## 13. Schedule automatic health checks

After the first manual build succeeds, open the job's **Configure → Build Triggers → Build periodically** and enter:

```text
H/30 * * * *
```

This runs approximately every 30 minutes. Jenkins' `H` spreads execution to a stable offset rather than starting every job at exactly minute 0. Use a less frequent schedule for a laptop lab if you do not keep the VMs running continuously.

## 14. Final URLs

- Jenkins: `http://192.168.56.10:8080`
- Dashboard: `http://192.168.56.10:5000`
- Linux target: `192.168.56.21`
- Windows target: `192.168.56.22`

## 15. Security and lab limitations

- The Vagrant `vagrant/vagrant` credentials are intentionally simple and only suitable for an isolated training lab.
- Keep the VirtualBox network host-only. Do not expose Jenkins, Flask, SSH or WinRM to the public internet.
- Use Jenkins Secret Text credentials for the vault password and Gmail App Password. Do not put secrets in the Jenkinsfile or GitHub.
- The dashboard is a lab dashboard and currently has no login layer. Do not publish it publicly.
- This is a starter implementation. For production, add dashboard authentication, TLS, secrets rotation, RBAC, persistent database storage, alert deduplication, stronger thresholds, and monitoring/observability for Jenkins itself.
- Windows checks use WinRM. Ansible's Windows connection plugin has separate Python dependencies; this project installs `pywinrm` in the controller virtual environment and uses the `ansible.windows` collection.

## Troubleshooting quick commands

```powershell
# On Windows host
vagrant status
vagrant reload controller
vagrant provision controller
```

```bash
# On Ubuntu controller
sudo systemctl status jenkins --no-pager
sudo systemctl status healthcheck-dashboard --no-pager
sudo journalctl -u jenkins -n 100 --no-pager
sudo journalctl -u healthcheck-dashboard -n 100 --no-pager
/opt/healthcheck/venv/bin/ansible linux -m ansible.builtin.ping --vault-password-file .vault-pass
/opt/healthcheck/venv/bin/ansible win01 -m ansible.windows.win_ping --vault-password-file .vault-pass
```
