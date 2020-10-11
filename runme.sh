#!/bin/bash

cd 'path/name/to/deployed/'
source ./bin/activate
export SPOTIPY_CLIENT_ID='MY_CLIENT_ID'
export SPOTIPY_CLIENT_SECRET='MY_CLIENT_SECRET'
export SPOTIPY_REDIRECT_URI='MY_REDIRECT_URI'
cd ./src
./main.py
deactivate
