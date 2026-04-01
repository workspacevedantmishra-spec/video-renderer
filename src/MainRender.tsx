import React from 'react';
import { AbsoluteFill, Audio, Video, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { MainRenderProps } from './Root';

export const MainRender: React.FC<MainRenderProps> = ({ videoUrl, audioUrl, subtitleScript }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const timeInSeconds = frame / fps;
  const totalDurationInSeconds = durationInFrames / fps;

  const words = subtitleScript.split(/\s+/).filter(Boolean);
  const timePerWord = totalDurationInSeconds / Math.max(1, words.length);

  const currentWordIndex = Math.floor(timeInSeconds / timePerWord);
  const currentWordText = currentWordIndex >= 0 && currentWordIndex < words.length ? words[currentWordIndex] : null;

  let scale = 1;
  if (currentWordText) {
    const wordStartFrame = Math.round(currentWordIndex * timePerWord * fps);
    const wordFrame = frame - wordStartFrame;

    // Apply a subtle scale-up animation on word-switches using Remotion's spring physics
    const springVal = spring({
      fps,
      frame: wordFrame,
      config: { damping: 14, mass: 0.6, stiffness: 120 },
      durationInFrames: 15,
    });
    
    // Interpolate the spring bounce to scale the pop from 0.85 -> 1.05 -> 1.0
    scale = interpolate(springVal, [0, 1], [0.85, 1.0]);
  }
  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      {videoUrl && (
        <Video 
          src={videoUrl} 
          muted={true}
          volume={0}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
        />
      )}
      {audioUrl && <Audio src={audioUrl} />}
      
      {currentWordText && (
        <div style={{
          position: 'absolute',
          top: '70%',
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 10
        }}>
          <div style={{
            fontSize: '75px',
            fontWeight: '900',
            color: '#FFD700', // High-contrast yellow
            WebkitTextStroke: '3px black', // Intense contrast bordering
            textShadow: '0 8px 16px rgba(0,0,0,0.9), 0 0 8px rgba(0,0,0,0.8)',
            backgroundColor: 'rgba(0, 0, 0, 0.4)',
            padding: '20px 45px',
            borderRadius: '20px',
            textAlign: 'center',
            fontFamily: '"Arial Black", Arial, sans-serif',
            maxWidth: '90%',
            lineHeight: '1.2',
            transform: `scale(${scale})`
          }}>
            {currentWordText}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
