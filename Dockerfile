FROM kbase/sdkpython:3.8.10
MAINTAINER KBase Developer

ENV DEBIAN_FRONTEND=noninteractive
RUN echo "start building docker image"

# minimal tools; no need for full build chain when using prebuilt SPAdes
RUN apt-get update \
 && apt-get -y install --no-install-recommends wget ca-certificates bzip2 pigz gcc \
 && rm -rf /var/lib/apt/lists/*

# Python bits some wrappers rely on
RUN pip3 install --upgrade pip \
 && pip3 install psutil \
 && python3 --version

# ----- SPAdes 4.2.0 (prebuilt Linux tarball) -----
ENV SPADES_VERSION="4.2.0"
WORKDIR /opt
RUN wget -q https://github.com/ablab/spades/releases/download/v${SPADES_VERSION}/SPAdes-${SPADES_VERSION}-Linux.tar.gz \
 && tar -xzf SPAdes-${SPADES_VERSION}-Linux.tar.gz \
 && rm SPAdes-${SPADES_VERSION}-Linux.tar.gz

# Add to PATH
ENV PATH="${PATH}:/opt/SPAdes-${SPADES_VERSION}-Linux/bin"

# Quick sanity checks (version + self-test)
RUN spades.py --version || true \
 && spades.py --test -o /tmp/spades_selftest || true

# -----------------------------------------
# Your module
COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module
RUN make

ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD []
