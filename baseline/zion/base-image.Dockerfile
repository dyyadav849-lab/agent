FROM docker-registry.gitlab.myteksi.net/library/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get -y upgrade && apt-get install -y bash git curl ssh awscli
