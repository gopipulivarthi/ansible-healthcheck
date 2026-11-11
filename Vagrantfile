Vagrant.configure("2") do |config|
  config.vm.box_check_update = false

  # VM 1: Ansible controller + Jenkins + Flask dashboard
  config.vm.define "controller" do |vm|
    vm.vm.box = "bento/ubuntu-24.04"
    vm.vm.hostname = "hc-controller"
    vm.vm.network "private_network", ip: "192.168.56.10"
    vm.vm.provider "virtualbox" do |vb|
      vb.name = "HC-Controller"
      vb.memory = 4096
      vb.cpus = 2
    end
    vm.vm.provision "shell", path: "scripts/bootstrap-controller.sh"
  end

  # VM 2: Linux managed node
  config.vm.define "linux01" do |vm|
    vm.vm.box = "bento/ubuntu-24.04"
    vm.vm.hostname = "linux01"
    vm.vm.network "private_network", ip: "192.168.56.21"
    vm.vm.provider "virtualbox" do |vb|
      vb.name = "HC-Linux-01"
      vb.memory = 1024
      vb.cpus = 1
    end
    vm.vm.provision "shell", path: "scripts/bootstrap-linux-target.sh"
  end

  # VM 3: Windows Server managed node (Vagrant box provides WinRM)
  config.vm.define "win01" do |vm|
    vm.vm.box = "gusztavvargadr/windows-server-2022-standard"
    vm.vm.box_version = "2607.0.0"
    vm.vm.guest = :windows
    vm.vm.communicator = "winrm"
    vm.vm.hostname = "win01"
    vm.vm.network "private_network", ip: "192.168.56.22"
    vm.vm.provider "virtualbox" do |vb|
      vb.name = "HC-Windows-01"
      vb.memory = 4096
      vb.cpus = 2
    end
  end
end
