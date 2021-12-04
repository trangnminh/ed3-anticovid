const express = require("express");
const http = require("http");
const socketIo = require("socket.io");

const port = process.env.PORT || 5000;

const app = express();
app.use(express.static('../public'));

const server = http.createServer(app);

const io = socketIo(server, {
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    }
  });

io.on("connection", (socket) => {
    console.log("New client connected");

    socket.on("disconnect", () => {
      console.log("Client disconnected");
    });

    socket.on('chat',function(data){
        io.sockets.emit('chat',data);
    })

    socket.on('login', function(data){
        io.sockets.emit('login',data);
    })

    socket.on('videoVision', function(data){
      let base64data = Buffer.from(data,'base64').toString('ascii')
      io.sockets.emit('videoVision',base64data);
    })
    socket.on('fpsMain',function(fps_data){
      io.sockets.emit('fpsMain',fps_data);
    });

    
  });

server.listen(port, () => console.log(`Listening on port ${port}`));