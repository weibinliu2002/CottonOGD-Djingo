// proxy.js
const net = require('net');

const LOCAL_PORT  = 3001;
const TARGET_HOST = '127.0.0.1';
const TARGET_PORT = 8002;

net.createServer(sock => {
  const upstream = net.createConnection(TARGET_PORT, TARGET_HOST);

  sock.pipe(upstream);
  upstream.pipe(sock);

  sock.on('error',  err => console.log('client error:',  err.message));
  upstream.on('error', err => console.log('upstream error:', err.message));
}).listen(LOCAL_PORT, '127.0.0.1');

console.log(`TCP proxy ready: 127.0.0.1:${LOCAL_PORT} -> ${TARGET_HOST}:${TARGET_PORT}`);