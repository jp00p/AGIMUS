FROM ubuntu:20.04


# Install apt dependencies
RUN rm /bin/sh && ln -s /bin/bash /bin/sh \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        curl wget apt-utils python3 python3-pip make build-essential fonts-noto-color-emoji locales openssl git jq tzdata sudo \
    && touch /etc/sudoers.d/bot-user \
    && echo "bot ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/bot-user \
    && useradd -ms /bin/bash bot \
    && usermod -aG sudo bot \
    && python3 -m pip install --upgrade --force pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3 /usr/local/bin/python

# configure timezone and set UTF8 charset
ENV TZ="America/Los_Angeles"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen
ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en

# Use 'bot' user to avoid pip warning messages
USER bot
# Add source code
WORKDIR /bot
COPY --chown=bot:bot . .
# Install requirements.txt with pip
RUN make setup

# Since requirements.txt can be mounted, run install again
# before running python.py in case of differences/updates
CMD make start
