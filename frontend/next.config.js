/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Suppress noisy webpack warnings from heavy packages like plotly.js
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // plotly.js uses some node builtins — tell webpack to ignore them
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      }
    }
    return config
  },
  // Allow cross-origin requests from Docker container
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
