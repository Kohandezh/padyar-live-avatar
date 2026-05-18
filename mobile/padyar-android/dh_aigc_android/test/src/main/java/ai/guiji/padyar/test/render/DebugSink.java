package ai.guiji.padyar.test.render;

import ai.guiji.padyar.sdk.client.bean.ImageFrame;
import ai.guiji.padyar.sdk.client.render.RenderSink;

public class DebugSink implements RenderSink {

    VideoFrameCallback callback;

    public DebugSink(VideoFrameCallback callback){
        this.callback = callback;
    }

    @Override
    public void onVideoFrame(ImageFrame imageFrame) {
        if (callback != null){
            callback.onVideoFrame(imageFrame);
        }
    }

    public interface VideoFrameCallback{
        void onVideoFrame(ImageFrame imageFrame);
    }
}
