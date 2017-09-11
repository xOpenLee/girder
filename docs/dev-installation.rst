
Developer Installation 
====================== 
 
You can either install Girder natively on you machine or inside a virtual
machine (VM) with Vagrant. 
 
Virtual Machine 
+++++++++++++++ 
 
The easiest way to develop for Girder is within a VM using Vagrant.
For this, you need `Vagrant <https://www.vagrantup.com/downloads.html>`_ and `VirtualBox <https://www.virtualbox.org/wiki/Downloads>`_. 
Girder is tested to work seamlessly with Vagrant 2.0 and VirtualBox 5.1. 
 
Once you have those installed, obtain the Girder source code by cloning the Git 
repository on `GitHub <https://github.com>`_:

.. code-block:: bash
 
    git clone https://github.com/girder/girder.git
    cd girder
 
Inside of the Girder directory, simply run:

.. code-block:: bash

    vagrant up

This creates a VM running Ubuntu 14.04, then automatically installs Girder
within it. After it completes, Girder will be up and running at
http://localhost:9080/ on the host machine.
 
The VM is linked to your local Girder directory, so changes made locally will
impact the Girder instance running in the VM.

To access the VM, from of the Girder directory, run:

.. code-block:: bash

    vagrant ssh

This takes you inside of VM. Navigate to the girder directory:

.. code-block:: bash

    cd girder

From here, you might want to restart the server:

.. code-block:: bash

    sudo service girder restart

rebuild the web client:

.. code-block:: bash

    girder-install web --dev

For more development documentation, see `During Development <development.html#during-development>`__
