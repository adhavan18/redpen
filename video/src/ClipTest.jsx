import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
export const ClipTest = ({ src }) => (
  <AbsoluteFill style={{ background: "#000" }}>
    <OffthreadVideo src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
  </AbsoluteFill>
);
