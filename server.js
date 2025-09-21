import express from 'express';
const app = express();
const port = process.env.PORT || 8080;
app.get('/', (_req, res) => res.send('ok'));
app.listen(port, '0.0.0.0', () => console.log('listening on', port));
