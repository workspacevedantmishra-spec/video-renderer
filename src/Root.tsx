import { Composition } from 'remotion';
import { MainRender } from './MainRender';
import React from 'react';

export type SubtitleItem = {
  start: number;
  end: number;
  text: string;
};

export type MainRenderProps = {
  videoUrl: string;
  audioUrl: string;
  subtitleScript: SubtitleItem[];
  durationInFrames?: number;
};

export const defaultProps: MainRenderProps = {
  videoUrl: 'https://cdn.pixabay.com/video/2021/08/04/83893-585806655_large.mp4',
  audioUrl: 'https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg',
  subtitleScript: [
    { start: 0, end: 1, text: 'Hello World!' }
  ],
  durationInFrames: 10800 // 3 minutes at 60fps
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainRender"
        component={MainRender}
        durationInFrames={defaultProps.durationInFrames || 10800}
        fps={60}
        width={1920}
        height={1080}
        defaultProps={defaultProps}
      />
    </>
  );
};
