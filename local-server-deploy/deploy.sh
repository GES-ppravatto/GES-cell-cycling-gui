#!/bin/bash

echo "GES-echem-gui installer script (version 0.1)"
echo "============================================================================="

INSTALL_DIR="/usr/share/GES-echem-gui"
CONDA_BASE_DIR=`conda info --base`
CONDA_ENV="GES-echem-gui-server"
GES_ECHEM_SUITE_REPO="https://github.com/GES-ppravatto/GES-echem-suite.git"
RC_LOCAL_FILE="/etc/rc.d/rc.local"

if [[ $1 == "install" ]]; then

	echo "GES-echem-gui install"
    echo "---------------------"

    echo "-> Fetching GES-echem-suite (latest)"
    git clone $GES_ECHEM_SUITE_REPO > "/dev/null"

    echo "-> Creating custom conda environment"
    conda create -y --name $CONDA_ENV python=3.8 > "/dev/null"

    echo "-> Installing requirements"
    source "$CONDA_BASE_DIR/etc/profile.d/conda.sh" > "/dev/null"
    conda activate $CONDA_ENV > "/dev/null"
    pip install -r "../requirements.txt" > "/dev/null"
    pip install "./GES-echem-suite" > "/dev/null"
    conda deactivate

    echo "-> Clean up downloaded files"
    rm -rf "./GES-echem-suite"

    echo "-> Creating custom launcher script"
    touch "./echem-gui-launcher.sh"
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

    echo "-> Generating rc.local file entry"
    touch "./new_rc_local.txt"
    if [[ -f "$RC_LOCAL_FILE" ]]; then
        echo "   -> rc.local file found"
        echo "   -> updating rc.local file"
        sudo sed "/exit 0/d" $RC_LOCAL_FILE >> "./new_rc_local.txt"
    else
        echo "   -> rc.local file not found"
        echo "   -> creating rc.local file"
        echo "#!/bin/sh -e" >> "./new_rc_local.txt"
    fi
    
    echo "sh $INSTALL_DIR/echem-gui-launcher.sh &" >> "./new_rc_local.txt"
    echo "exit 0" >> "./new_rc_local.txt"
    sudo mv "./new_rc_local.txt" $RC_LOCAL_FILE
    sudo chown root $RC_LOCAL_FILE
    sudo chmod 755 $RC_LOCAL_FILE

    echo "-> Adding http firewall rule (port 80)"
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --reload
    sudo systemctl restart firewalld.service

    echo "-> Starting streamlit server"
    sudo nohup "$INSTALL_DIR/echem-gui-launcher.sh" 

elif [[ $1 == "remove" ]]; then
	echo "GES-echem-gui uninstall"

    echo "-> Removing http firewall rule (port 80) and restart"
    sudo firewall-cmd --permanent --remove-service=http
    sudo firewall-cmd --reload
    sudo systemctl restart firewalld.service

    echo "-> Cleaning the rc.local file"
    sudo cp $RC_LOCAL_FILE "./old_rc_local.txt"
    sed -i "/echem-gui-launcher.sh/d" "./old_rc_local.txt"
    sudo mv "./old_rc_local.txt" $RC_LOCAL_FILE

    echo "-> Removing installed files"
    sudo rm -rf $INSTALL_DIR

    echo "-> Removing conda environment"
    source "$CONDA_BASE_DIR/etc/profile.d/conda.sh" > "/dev/null"
    conda remove -y --name $CONDA_ENV --all > "/dev/null"


else
	echo "ERROR: '$1' is not a valid command"

fi	