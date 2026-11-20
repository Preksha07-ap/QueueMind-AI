import React, { useRef, useEffect } from 'react';

/**
 * CinematicBackground — Full-viewport video background with dark overlay.
 * Uses a ref to prevent video restart on route changes within AuthLayout.
 */
export const CinematicBackground: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // Ensure video plays on mount (browser autoplay policy requires muted)
    videoRef.current?.play().catch(() => {});
  }, []);

  return (
    <div className="fixed inset-0 z-0 overflow-hidden">
      {/* Video */}
      <video
        ref={videoRef}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        className="absolute inset-0 w-full h-full object-cover"
        style={{ filter: 'brightness(0.85) saturate(1.15)' }}
      >
        <source
          src="/videos/Untitled_Scene_11-19_14_44_37_20261120040856.mp4"
          type="video/mp4"
        />
      </video>

      {/* Dark gradient overlay - carefully balanced for brightness and text contrast */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            linear-gradient(180deg,
              rgba(8, 13, 27, 0.52) 0%,
              rgba(8, 13, 27, 0.36) 40%,
              rgba(8, 13, 27, 0.46) 70%,
              rgba(8, 13, 27, 0.72) 100%
            )
          `,
        }}
      />

      {/* Subtle noise texture overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  );
};
