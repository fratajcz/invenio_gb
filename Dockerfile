ARG LINUX_VERSION=10.1
ARG BUILDPLATFORM=linux/amd64
FROM --platform=$BUILDPLATFORM almalinux:${LINUX_VERSION}

RUN dnf upgrade --refresh -y && \
    dnf install -y \
        dnf-plugins-core \
        git \
        glibc-common \
        glibc-locale-source \
        glibc-langpack-en \
        gcc

RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

ENV LANG=en_US.UTF8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# EPEL: Extra Packages for Enterprise Linux 9
# `epel-release` is not recent/complete enough, as some packages below are missing
RUN dnf config-manager --set-enabled crb && \
    dnf install -y \
        https://dl.fedoraproject.org/pub/epel/epel-release-latest-10.noarch.rpm

# Install needed and useful tools:
#  - python and friends
#  - basic system tools (procps-ng, htop, less, git, glibc, wget, curl)
#  - process/file inspection tools (strace, lsof, file)
#  - performance monitoring tools (iotop, iftop)
#  - networking tools (tcpdump, bind-utils)
# The installation of "Development Tools" should not be required. Be aware of its
# size ~1.1 Gb
RUN dnf install -y \
        pip \
        python3-devel \
        cairo-devel \
        dejavu-sans-fonts \
        libffi-devel \
        libpq-devel \
        libxml2-devel \
        libxslt-devel \
        ImageMagick \
        openssl-devel \
        bzip2-devel \
        xz-devel \
        sqlite-devel \
        xmlsec1-devel \
        procps-ng htop less \
        strace lsof file \
        iotop iftop \
        tcpdump bind-utils

RUN dnf remove six && rm -rf /usr/lib/python3.12/site-packages/six*
# Symlink Python
RUN ln -sfn /usr/bin/python3 /usr/bin/python
# `python3-packaging` is installed by `yum` and it causes issues with `pip` installations
RUN yum remove python3-packaging -y
RUN pip3 install --upgrade pip pipenv wheel

# Install Node.js
RUN curl -fsSL https://rpm.nodesource.com/setup_26.x | bash - && \
    dnf -y install nodejs

# Reduce image size: clean up caches, remove RPM db files
#RUN dnf clean all && \
#    rm -rf \
#        /var/cache/dnf \
#        /var/lib/rpm/__db* \
#        /var/lib/rpm/rpmdb.sqlite \
#        /var/lib/rpm/Packages

# Create working directory
ENV WORKING_DIR=/opt/invenio
ENV INVENIO_INSTANCE_PATH=${WORKING_DIR}/var/instance

# Create files mountpoints
RUN mkdir -p ${WORKING_DIR}/src && \
    mkdir -p ${INVENIO_INSTANCE_PATH} && \
    mkdir \
        ${INVENIO_INSTANCE_PATH}/data \
        ${INVENIO_INSTANCE_PATH}/archive \
        ${INVENIO_INSTANCE_PATH}/static

# Invenio file will be in <WORKING_DIR>/src
WORKDIR ${WORKING_DIR}/src

# Set folder permissions


####### now we start with the setup part


ENV KEYTAB_PATH='/var/lib/secrets'
ENV KERBEROS_TOKEN_PATH='/var/run/krb5-tokens'

RUN dnf install -y epel-release
RUN dnf update -y
RUN dnf install -y yum-utils kstart krb5-workstation && dnf clean all

VOLUME ["${KERBEROS_TOKEN_PATH}"]

RUN mkdir -p $KEYTAB_PATH && chmod a+rw $KEYTAB_PATH

COPY site ./site
COPY Pipfile Pipfile.lock ./
#RUN pipenv --system --python 3.12
#RUN pip install pipenv && python -m pipenv install --deploy --system

RUN pipenv requirements > requirements.txt && pip install -r requirements.txt && pip cache purge
# next 2 lines also from demo
#RUN dnf install -y cmake libuuid-devel && dnf clean all
#RUN pip install invenio-xrootd>=2.0.0a1 && pip cache purge

COPY ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}
COPY ./invenio.cfg ${INVENIO_INSTANCE_PATH}
COPY ./templates/ ${INVENIO_INSTANCE_PATH}/templates/
COPY ./app_data/ ${INVENIO_INSTANCE_PATH}/app_data/
COPY ./translations/ ${INVENIO_INSTANCE_PATH}/translations/
COPY ./ .

RUN cp -r ./static/. ${INVENIO_INSTANCE_PATH}/static/ && \
    cp -r ./assets/. ${INVENIO_INSTANCE_PATH}/assets/ && \
    pipenv run invenio collect --verbose  && \
    pipenv run invenio webpack buildall

# rest is also from demo

# application build args to be exposed as environment variables
ARG IMAGE_BUILD_TIMESTAMP
ARG SENTRY_RELEASE

# Expose random sha to uniquely identify this build
ENV INVENIO_IMAGE_BUILD_TIMESTAMP="'${IMAGE_BUILD_TIMESTAMP}'"
ENV SENTRY_RELEASE=${SENTRY_RELEASE}

RUN pipenv --clear
RUN echo "Image build timestamp $INVENIO_IMAGE_BUILD_TIMESTAMP"

ENV INVENIO_USER_ID=1000
RUN chgrp -R 0 ${WORKING_DIR} && \
    chmod -R g=u ${WORKING_DIR} && \
    useradd invenio --uid ${INVENIO_USER_ID} --gid 0 && \
    chown -R invenio:root ${WORKING_DIR}

USER ${INVENIO_USER_ID}:${INVENIO_USER_ID}

ENTRYPOINT [ "bash", "-c"]