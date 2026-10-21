import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "kopis.or.kr", pathname: "/upload/pfmPoster/**" },
      { protocol: "https", hostname: "ticketimage.interpark.com" },
      { protocol: "https", hostname: "www.bac.or.kr" },
    ],
  },
  turbopack: {
    root: path.resolve(process.cwd(), "../.."),
  },
  transpilePackages: ["@classic-hubble/shared"],
};

export default nextConfig;
