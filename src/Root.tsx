import { Composition, CalculateMetadataFunction } from 'remotion';
import { getAudioDurationInSeconds } from '@remotion/media-utils';
import { MainRender } from './MainRender';
import React from 'react';

export type MainRenderProps = {
  videoUrl: string;
  audioUrl: string;
  subtitleScript: string;
  durationInFrames?: number;
};

export const defaultProps: MainRenderProps = {
  videoUrl: 'https://cdn.pixabay.com/video/2021/08/04/83893-585806655_large.mp4',
  audioUrl: 'https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg',
  subtitleScript: "This is a normal text script that will be automatically synced over the full audio track length.",
  durationInFrames: 5400 // Safe default fallback (3 mins at 30fps)
};

export const calculateMetadata: CalculateMetadataFunction<MainRenderProps> = async ({ props }) => {
  try {
    const duration = await getAudioDurationInSeconds(props.audioUrl);
    return {
      durationInFrames: Math.max(30, Math.ceil(duration * 30))
    };
  } catch (e) {
    console.error("Could not fetch audio metadata:", e);
    return {
      durationInFrames: props.durationInFrames || 5400
    };
  }
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainRender"
        component={MainRender}
        calculateMetadata={calculateMetadata}
        defaultProps={defaultProps}
        fps={30}
        width={720}
        height={1280}
      />
    </>
  );
};
