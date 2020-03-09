# DESCRIPTION
For YouTube video url signature parse

# DEMO
https://ytsig.herokuapp.com

## CONFIG
For PORT and HTTPS settings  
We suggest that just set HTTPS enable for production use
- index.js

## SSL
To use HTTPS, you should overwrite the test file, gen and sign by yourself or aplly for it  
https://letsencrypt.org/ is a suggestion
- server.cert: certificate of server
- server.key: private key of server

## Run step
``` bash
# install dependencies(just for the first time)
npm i

# start or restart server
npm run product
```
## Key list API
- Do "Run step" once
- Add the key file to api key path which config in index.js, keep file name 0-n.key,There are 3 demos
 
