package ai.guiji.padyar.sdk.client;

public interface Callback {

    void onEvent(String event, String msg, Object info);

}