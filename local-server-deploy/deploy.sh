#!/bin/bash

echo "GES-echem-gui installer script (version 0.1)"
echo "============================================================================="

INSTALL_DIR="/usr/share/GES-echem-gui"
CONDA_BASE_DIR=`conda info --base`
CONDA_ENV="GES-echem-gui-server"
GES_ECHEM_SUITE_REPO="https://github.com/GES-ppravatto/GES-echem-suite.git"
SYSTEMD_SERVICE="/etc/systemd/system/ges-echem-gui.service"

if [[ $1 == "install" ]]; then

	echo "GES-echem-gui install"
    echo "---------------------"

    echo "-> Fetching GES-echem-suite (latest)"
    git clone $GES_ECHEM_SUITE_REPO > "/dev/null"

    echo "-> Creating custom conda environment"
    conda create -y --name $CONDA_ENV python=3.8 > "/dev/null"

    echo "-> Installing requirements in the conda environment"
    source "$CONDA_BASE_DIR/etc/profile.d/conda.sh" > "/dev/null"
    conda activate $CONDA_ENV > "/dev/null"
    pip install -r "../requirements.txt" > "/dev/null"
    pip install "./GES-echem-suite" > "/dev/null"
    conda deactivate

    echo "-> Cleaning up downloaded files"
    rm -rf "./GES-echem-suite"

    echo "-> Creating custom launcher script"
    echo "#!/bin/bash" >> "./echem-gui-launcher.sh"
    echo "source $CONDA_BASE_DIR/etc/profile.d/conda.sh" >> "./echem-gui-launcher.sh"
    echo "conda activate $CONDA_ENV" >> "./echem-gui-launcher.sh"
    echo "streamlit run $INSTALL_DIR/cell-cycling/file_manager.py --server.port 80" >> "./echem-gui-launcher.sh"
    chmod +x "./echem-gui-launcher.sh"

    echo "-> Creating installation folder"
    sudo mkdir $INSTALL_DIR

    echo "-> Setting up installation"
    echo "   -> Copying GUI code"
    sudo cp -r "../cell-cycling" $INSTALL_DIR

    echo "   -> Moving launcher script"
    sudo mv "./echem-gui-launcher.sh" $INSTALL_DIR

    echo "-> Creating a custom ges-echem-gui service"
    echo "[Unit]" > "./service.txt"
    echo "Description=GES-echem-gui http page service" >> "./service.txt"
    echo "" >> "./service.txt"
    echo "[Service]" >> "./service.txt"
    echo "ExecStart=$INSTALL_DIR/echem-gui-launcher.sh" >> "./service.txt"
    echo "" >> "./service.txt"
    echo "[Install]" >> "./service.txt"
    echo "WantedBy=multi-user.target" >> "./service.txt"
    sudo mv "./service.txt" $SYSTEMD_SERVICE
    sudo systemctl daemon-reload

    echo "-> Adding http firewall rule (port 80)"
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --reload
    sudo systemctl restart firewalld.service

    echo "-> Starting and enabling the ges-echem-gui service"
    sudo systemctl start ges-echem-gui.service
    sudo systemctl enable ges-echem-gui.service

    exit 0

elif [[ $1 == "remove" ]]; then
	echo "GES-echem-gui uninstall"

    echo "-> Removing http firewall rule (port 80) and restart"
    sudo firewall-cmd --permanent --remove-service=http
    sudo firewall-cmd --reload
    sudo systemctl restart firewalld.service

    echo "-> Stopping and disabling the ges-echem-gui service"
    sudo systemctl stop ges-echem-gui.service
    sudo systemctl disable ges-echem-gui.service

    echo "-> Removing the ges-echem-gui service"
    sudo rm $SYSTEMD_SERVICE

    echo "-> Removing installed files"
    sudo rm -rf $INSTALL_DIR

    echo "-> Removing conda environment"
    source "$CONDA_BASE_DIR/etc/profile.d/conda.sh" > "/dev/null"
    conda remove -y --name $CONDA_ENV --all > "/dev/null"


else
	echo "ERROR: '$1' is not a valid command"

fi	