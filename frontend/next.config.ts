/** @type {import('next').NextConfig} */
const nextConfig = {
  // Authorize our explicit local port bounds and network switches
  allowedDevOrigins: [
    "localhost:3000",
    "localhost:3001",
    "127.0.0.1:3000",
    "127.0.0.1:3001",
    "192.168.1.12:3000",
    "192.168.1.12:3001",
    "172.23.112.1:3000",
    "172.23.112.1:3001",
    "172.23.112.1"
  ]
};

export default nextConfig;