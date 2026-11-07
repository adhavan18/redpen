import { Composition } from "remotion";
import { Demo, totalFrames, FPS } from "./Demo";
import { Launch, totalLaunchFrames } from "./Launch";
import { ClipTest } from "./ClipTest";

export const Root = () => (
  <>
    <Composition id="Launch" component={Launch} durationInFrames={totalLaunchFrames} fps={30} width={1920} height={1080} />
    <Composition id="Demo" component={Demo} durationInFrames={totalFrames(false)} fps={FPS} width={1920} height={1080}
                 defaultProps={{ subtitles: false }} />
    <Composition id="DemoSubtitled" component={Demo} durationInFrames={totalFrames(true)} fps={FPS} width={1920} height={1080}
                 defaultProps={{ subtitles: true }} />
    <Composition id="ClipTest" component={ClipTest} durationInFrames={60} fps={30} width={1024} height={576}
                 defaultProps={{ src: "clips/c02.mp4" }} />
  </>
);
