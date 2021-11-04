#!/bin/bash

cmd1="python httpc.py -v get 'localhost:8080/'"
cmd2="python httpc.py -v get 'localhost:8080/file1.txt'"
cmd3="python httpc.py -v post 'localhost:8080/file2.txt' -d 'data from post request'"
cmd4="python httpc.py -v get 'localhost:8080/file2.txt'"
cmd5="python httpc.py -v get 'localhost:8080/../httpfs.py'"
cmd6="python httpc.py -v get 'localhost:8080/not_existed_file.txt'"

all_cmds=("$cmd1" "$cmd2" "$cmd3" "$cmd4" "$cmd5" "$cmd6")

for c in "${all_cmds[@]}"
do
  read
  echo "----------------------------------------------------------------------------------"
  echo "$c"
  echo ""
  eval "$c"
done

read
echo "-------- Writing to the same file ---------------------------------------------------"
cmd7="python httpc.py -v post 'localhost:8080/file3.txt' -d 'write from client1' -h 'append:True'"
cmd8="python httpc.py -v post 'localhost:8080/file3.txt' -d 'write from client2' -h 'append:True'"
eval "$cmd7"
eval "$cmd8"

read
echo "--------- One reading, one writing ---------------------------------------------------"
cmd9="python httpc.py -v get 'localhost:8080/file4.txt'"
cmd10="python httpc.py -v post 'localhost:8080/file4.txt' -d 'write from cmd'"
eval "$cmd9"
eval "$cmd10"

read
echo "--------- Two clients reading ---------------------------------------------------"
cmd9="python httpc.py -v get 'localhost:8080/file5.txt'"
cmd10="python httpc.py -v get 'localhost:8080/file5.txt'"
eval "$cmd9"
eval "$cmd10"
