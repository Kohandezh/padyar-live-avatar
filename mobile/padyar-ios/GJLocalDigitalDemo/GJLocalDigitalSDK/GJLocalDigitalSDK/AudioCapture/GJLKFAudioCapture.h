
#import <Foundation/Foundation.h>
#import <CoreMedia/CoreMedia.h>
#import "GJLKFAudioConfig.h"
#import "GJLAudioPlayer.h"
NS_ASSUME_NONNULL_BEGIN

@interface GJLKFAudioCapture : NSObject

+ (instancetype)new NS_UNAVAILABLE;
- (instancetype)init NS_UNAVAILABLE;
- (instancetype)initWithConfig:(GJLKFAudioConfig *)config;

@property (nonatomic, strong, readonly) GJLKFAudioConfig *config;
@property (nonatomic, assign) AudioStreamBasicDescription audioFormat; // 音频采集参数。
@property (nonatomic, assign)Float64 durationInSeconds;//音频总时长

//一句话或一段话结束
@property (nonatomic, assign)BOOL isFinish;
//0 录音数据 1 播放数据
@property (nonatomic, copy) void (^sampleBufferOutputCallBack)(CMSampleBufferRef sample,NSInteger type); // 音频采集数据回调。
@property (nonatomic, copy) void (^audioPCMDataCallBack)(NSData * data,NSInteger level); // 音频采集数据回调。
//@property (nonatomic, copy) void (^audioBufferInputCallBack)(AudioBufferList *audioBufferList); // 音频渲染数据输入回调。
@property (nonatomic, copy) void (^errorCallBack)(NSError *error); // 音频采集错误回调。
@property (nonatomic, copy) void (^audioBufferInputCallBack)(AudioBufferList *audioBufferList); // 音频渲染数据输入回调。
//@property (nonatomic, copy) void (^sampleBufferInputCallBack)(CMSampleBufferRef sample); //音频渲染数据输入回调。
////播放状态回调
@property (nonatomic, copy) void (^playFailed)(void);
//播放结束回调
@property (nonatomic, copy) void (^playEnd)(void);
//播放进度回调
@property (nonatomic, copy) void (^playProgress)(float current,float total);
// 已读的音频帧个数
@property (nonatomic, assign) SInt64 readedSize;
@property (nonatomic, assign) BOOL isRunning;
//一句话或一段话的长度
@property (nonatomic, assign) int dataLengh;

- (void)startRunning; // 开始采集音频数据。
- (void)stopRunning; // 停止采集音频数据。
-(void)pauseRunning:(BOOL)pause; //暂停采集

- (void)startPlaying; // 开始渲染。
- (void)stopPlaying:(void (^)( BOOL isSuccess))success; // 结束渲染。
-(void)toFree;
///*
//*dataLength 音频buffer的长度
//*isFinish 是否一句话结束或者整段话结束
//*/
-(void)toBufferLength:(int)dataLength isFinish:(BOOL)isFinish;



// 重置AudioUnit状态
- (void)resetAudioUnit;

- (void)toSetVolume:(float)volume;

-(void)toMuteRecord:(BOOL)isMute;
@end

NS_ASSUME_NONNULL_END
