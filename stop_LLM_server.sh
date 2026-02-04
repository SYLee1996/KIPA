
pkill -f "port 8000" 
pkill -f "port 9000" 

fuser -k 8000/tcp
fuser -k 9000/tcp