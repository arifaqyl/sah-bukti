import React from "react";
import {Composition, registerRoot} from "remotion";
import {SahBuktiDemo} from "./SahBuktiDemo";

const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="SahBuktiDemo"
        component={SahBuktiDemo}
        durationInFrames={4320}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};

registerRoot(RemotionRoot);
