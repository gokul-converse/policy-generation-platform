import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  async redirects() {
    return [
      {
        source: '/policy-studio',
        destination: '/',
        permanent: false,
      },
      {
        source: '/policy-studio/requirements',
        destination: '/',
        permanent: false,
      },
      {
        source: '/policy-studio/skills',
        destination: '/skills',
        permanent: false,
      },
      {
        source: '/policy-studio/policy-review',
        destination: '/policy-review',
        permanent: false,
      },
      {
        source: '/policy-studio/preview',
        destination: '/preview',
        permanent: false,
      },
      {
        source: '/policy-studio/master-policy',
        destination: '/master-policy',
        permanent: false,
      },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
