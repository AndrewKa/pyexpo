FROM centos:latest

RUN yum update && yum install -y \
    vim-enhanced \
    bash-completion \
    python-setuptools \
    && easy_install pip
RUN pip install click #\
    #jedi #for vim-jedi
#bpython? ipython? prompt-toolkit?

WORKDIR /opt/pyprojects/pyexpo/src
RUN python setup.py develop

CMD ["/bin/bash"]

