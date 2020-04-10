const app = new (require('koa'))()
  , net = require('net')
  , send = require('koa-send')
  , fs = require('fs')
  , config = require('./config');

const util = require('util');
const readdir = util.promisify(fs.readdir);
const { execFile } = require('child_process');
var child = execFile('python', ['external/s.py'], (error, stdout) => {
  if (error) {
    return child.kill()
  }
  console.log(stdout);
})

app.use(async ctx => {
  const { s, js } = ctx.request.query

  if ('/api/keylist' == ctx.path) {
    ctx.set('Content-Type', 'text/plain')

    let files;
    try {
      files = await readdir(config.KEY_PATH);
    } catch (err) {
      console.log(err);
      ctx.body = 'read api err'
      return;
    }
    if (files && files.length) {
      id = Math.floor(Math.random() * files.length);
      await send(ctx, `${config.KEY_PATH}/${id}.key`);
    }
    else {
      ctx.body = 'read apilist err'
    }
  }
  else if (s && js) {
    return new Promise(function (resolve, reject) {
      var client = net.createConnection({ port: 3001 }, () => {
        client.write(s + ' ' + js)
      }).on('data', data => {
        ctx.body = data.toString();
        resolve()
        client.destroy();
      }).on('error', data => {
        ctx.status = 501
        resolve()
        client.destroy();
      })
    })
  }
  else {
    ctx.body = `
    <h1>Welcome</h1>
    <a href='?s=6D6D5247217C2EB22945406888C21FD775B3209065.28F3AA41915594D913C730C6309B9A03C23BCDFDFD&js=/yts/jsbin/player-vflu-7yX5/en_US/base.js'>
     This is a demo...</a>
    `
  }
})

if (config.ENABLE_HTTP) {
  require('http')
    .createServer(app.callback())
    .listen(process.env.PORT || config.HTTP_PORT)
    .on('listening', function () {
      console.log('http listening ' + this.address().port)
    })
}

if (config.ENABLE_HTTPS) {
  const fs = require('fs')
  require('https')
    .createServer({
      key: fs.readFileSync('./config/server.key'),
      cert: fs.readFileSync('./config/server.cert')
    }, app.callback())
    .listen(config.HTTPS_PORT)
    .on('listening', function () {
      console.log('https listening ' + this.address().port)
    })
}
