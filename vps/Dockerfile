FROM python:3.9

RUN apt-get update
# Installing Rust
RUN curl --proto '=https' --tlsv1.3 https://sh.rustup.rs -sSf | sh -s -- -y
RUN echo 'source $HOME/.cargo/env' >> $HOME/.bashrc

RUN apt-get install build-essential libsndfile-dev ffmpeg -y

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN pip install https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz

COPY . .