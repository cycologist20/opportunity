/** @type {import('next').NextConfig} */
const nextConfig = {
  // produce a fully static site in ./out
  output: 'export',
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // if you use next/image anywhere
  images: {
    unoptimized: true,
  },
  // optional: if you prefer /about/ instead of /about
  // trailingSlash: true,
}

export default nextConfig
